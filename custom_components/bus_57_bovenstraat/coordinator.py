"""Coordinator for Bus 57 Bovenstraat."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace
from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import TransitHttpClient, TransitHttpError
from .const import (
    ACTIVE_JOURNEY_MAX_AGE,
    DATA_OWNER,
    DESTINATION,
    INVALID_JOURNEY_REMEMBER,
    LINE_PLANNING_NUMBER,
    LINE_PUBLIC_NUMBER,
    MAX_EARLY_SECONDS,
    NAME,
    PASSED_JOURNEY_REMEMBER,
    PSA_RETRY_INTERVAL,
    REALTIME_STALE_AFTER,
    RECENT_KV6_EVENTS,
    TARGET_STOP_PLACE_CODE,
    TRUSTED_KV6_SOURCE,
    UPDATE_INTERVAL,
)
from .models import BusSnapshot, JourneySelection, Kv6Event
from .realtime import Kv6Subscriber

_LOGGER = logging.getLogger(__name__)

# DELAY alone can exist before a vehicle is physically executing the trip. The
# four state/position events below are therefore the only events that may make
# the Home Assistant sensors available.
_UNDERWAY_EVENTS = {"ONROUTE", "ARRIVAL", "ONSTOP", "DEPARTURE"}
_DELAY_EVENTS = _UNDERWAY_EVENTS


class Bus57Coordinator(DataUpdateCoordinator[BusSnapshot]):
    """Combine journey selection, official stop mapping and raw Arriva KV6."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TransitHttpClient,
    ) -> None:
        self._client = client
        self._kv6 = Kv6Subscriber()
        self._kv6_task: asyncio.Task[None] | None = None
        self._active: JourneySelection | None = None
        self._recent_events: deque[Kv6Event] = deque(maxlen=RECENT_KV6_EVENTS)
        self._passed_journeys: dict[str, datetime] = {}
        self._invalid_journeys: dict[str, datetime] = {}
        self._selection_error: str | None = None

        # Official BISON PassengerStopAssignment normalization table:
        # ARR UserStopCode -> national CHB StopPlaceCode.
        self._stop_place_by_user_stop: dict[str, str] = {}
        self._psa_refresh_day = None
        self._psa_retry_after: datetime | None = None

        # PassageSequenceNumber is NOT a global route stop order. BISON defines
        # it per UserStopCode. Timestamp is therefore used for out-of-order
        # stop-progress protection instead.
        self._last_stop_progress_timestamp: datetime | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=NAME,
            config_entry=entry,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )

        self.data = BusSnapshot(
            line=LINE_PUBLIC_NUMBER,
            destination=DESTINATION,
        )

    @property
    def timing_point_code(self) -> str:
        """Compatibility attribute: national target StopPlaceCode."""
        return TARGET_STOP_PLACE_CODE

    @property
    def line_id(self) -> str:
        return f"{DATA_OWNER}:{LINE_PLANNING_NUMBER}"

    @property
    def realtime_connected(self) -> bool:
        return self._kv6.connected

    @property
    def selection_error(self) -> str | None:
        return self._selection_error

    async def async_start(self) -> None:
        """Start realtime input, load official stop mapping and select a bus."""
        self.async_set_updated_data(self.data)

        # Start KV6 first so relevant vehicle events are cached while the small
        # HTTP/bootstrap requests are in progress.
        self._kv6_task = asyncio.create_task(
            self._kv6.async_run(self._async_handle_kv6_event),
            name="bus_57_bovenstraat_kv6",
        )

        await self._async_refresh_psa(silent=True)

        try:
            await self._async_select_journey()
        except TransitHttpError as err:
            self._selection_error = str(err)
            _LOGGER.warning("Initial Bus 57 journey selection failed: %s", err)

    async def async_shutdown(self) -> None:
        await self._kv6.async_stop()
        if self._kv6_task is not None:
            self._kv6_task.cancel()
            try:
                await self._kv6_task
            except asyncio.CancelledError:
                pass
            self._kv6_task = None

    async def _async_refresh_psa(self, *, silent: bool = False) -> None:
        """Refresh UserStopCode normalization without making setup fail."""
        try:
            mapping = await self._client.async_get_passenger_stop_assignments()
        except TransitHttpError as err:
            self._psa_retry_after = dt_util.now() + PSA_RETRY_INTERVAL
            if not silent:
                _LOGGER.warning("PassengerStopAssignment refresh failed: %s", err)
            else:
                _LOGGER.debug("Initial PassengerStopAssignment load failed: %s", err)
            return

        self._stop_place_by_user_stop = mapping
        self._psa_refresh_day = dt_util.now().date()
        self._psa_retry_after = None

        target_user_codes = sum(
            1
            for stop_place in mapping.values()
            if stop_place == TARGET_STOP_PLACE_CODE
        )
        _LOGGER.info(
            "Loaded %d active Arriva PassengerStopAssignments from %s; "
            "%d UserStopCode(s) map to Bovenstraat",
            len(mapping),
            self._client.psa_filename or "NDOV",
            target_user_codes,
        )

    async def _async_update_data(self) -> BusSnapshot:
        """Perform lightweight maintenance; live data itself is push-driven."""
        self._expire_journey_filters()
        now = dt_util.now()

        # Refresh the ~1 MB compressed official mapping at most once per local
        # day; after a failed initial download retry only every five minutes.
        psa_due = self._psa_refresh_day != now.date()
        retry_due = self._psa_retry_after is not None and now >= self._psa_retry_after
        if psa_due and (self._psa_retry_after is None or retry_due):
            await self._async_refresh_psa()

        # A live bus must keep producing trusted vehicle-origin KV6 messages.
        if (
            self.data.is_underway
            and self.data.data_timestamp is not None
            and (now - self.data.data_timestamp) > REALTIME_STALE_AFTER
        ):
            self.data = replace(
                self.data,
                is_underway=False,
                delay_seconds=None,
                delay_source_stop=None,
                delay_source_status=None,
                delay_observed_at=None,
                last_passed_stop=None,
                last_passed_stop_code=None,
                realtime_connected=self._kv6.connected,
            )

        if self._active is not None:
            scheduled = self._active.scheduled_bovenstraat
            if scheduled is not None and (now - scheduled) > ACTIVE_JOURNEY_MAX_AGE:
                _LOGGER.warning("Dropping stale Bus 57 journey %s", self._active.key)
                self._active = None
                self._last_stop_progress_timestamp = None
                self.data = BusSnapshot(
                    line=LINE_PUBLIC_NUMBER,
                    destination=DESTINATION,
                    realtime_connected=self._kv6.connected,
                )

        if self._active is None:
            try:
                await self._async_select_journey()
                self._selection_error = None
            except TransitHttpError as err:
                self._selection_error = str(err)
                raise UpdateFailed(f"Journey selection failed: {err}") from err

        return replace(self.data, realtime_connected=self._kv6.connected)

    async def _async_select_journey(self) -> None:
        """Choose the current/next line 57 to Maastricht."""
        candidates = await self._client.async_get_bovenstraat_journeys()
        self._expire_journey_filters()

        chosen = next(
            (
                candidate
                for candidate in candidates
                if candidate.key not in self._passed_journeys
                and candidate.key not in self._invalid_journeys
            ),
            None,
        )

        if chosen is None:
            self._active = None
            self._last_stop_progress_timestamp = None
            self.async_set_updated_data(
                BusSnapshot(
                    line=LINE_PUBLIC_NUMBER,
                    destination=DESTINATION,
                    realtime_connected=self._kv6.connected,
                )
            )
            return

        if self._active is not None and self._active.key == chosen.key:
            return

        self._active = chosen
        self._last_stop_progress_timestamp = None
        snapshot = BusSnapshot(
            journey_number=chosen.journey_number,
            operating_day=chosen.operating_day,
            journey_key=chosen.key,
            line=LINE_PUBLIC_NUMBER,
            destination=DESTINATION,
            is_underway=False,
            target_scheduled_time=chosen.scheduled_bovenstraat,
            realtime_connected=self._kv6.connected,
        )
        self.async_set_updated_data(snapshot)
        _LOGGER.info("Tracking Bus 57 journey %s", chosen.key)

        # Re-apply only trusted physical-vehicle events that arrived while the
        # timetable/PSA bootstrap was being processed.
        for event in tuple(self._recent_events):
            if not self._event_matches_active(event):
                continue
            if self._is_implausibly_early(event):
                await self._async_reject_active_journey(event)
                return
            await self._async_apply_event(event)

    async def _async_handle_kv6_event(self, event: Kv6Event) -> None:
        """Retain only trustworthy physical events for the planned line-57 bus."""
        if event.data_owner_code and event.data_owner_code != DATA_OWNER:
            return
        if event.line_planning_number != LINE_PLANNING_NUMBER:
            return

        # ReinforcementNumber >0 is an additional vehicle on the same public
        # journey and must not be mixed with the planned vehicle.
        if event.reinforcement_number not in (None, 0):
            return

        # BISON Source explicitly distinguishes vehicle-origin and server-origin
        # records. SERVER records can be synthetic and are not sufficient proof
        # that a physical bus is currently driving. A non-zero vehicle number is
        # required as an additional sanity check.
        if not self._is_trusted_vehicle_event(event):
            return

        self._recent_events.append(event)
        if not self._event_matches_active(event):
            return

        if self._is_implausibly_early(event):
            await self._async_reject_active_journey(event)
            return

        if event.event_type == "END":
            await self._async_finish_active_journey("END")
            return

        await self._async_apply_event(event)

    @staticmethod
    def _is_trusted_vehicle_event(event: Kv6Event) -> bool:
        source = (event.source or "").upper()
        vehicle = (event.vehicle_number or "").strip()
        return source == TRUSTED_KV6_SOURCE and vehicle not in {"", "0"}

    def _event_matches_active(self, event: Kv6Event) -> bool:
        active = self._active
        if active is None:
            return False
        return (
            event.journey_number == active.journey_number
            and event.operating_day == active.operating_day
            and event.reinforcement_number in (None, 0)
        )

    @staticmethod
    def _is_implausibly_early(event: Kv6Event) -> bool:
        return (
            event.event_type in _DELAY_EVENTS
            and event.punctuality is not None
            and event.punctuality < -MAX_EARLY_SECONDS
        )

    async def _async_reject_active_journey(self, event: Kv6Event) -> None:
        """Blacklist a physically reported but impossible journey and reselect."""
        active = self._active
        if active is None:
            return

        _LOGGER.warning(
            "Ignoring Bus 57 journey %s: trusted vehicle %s reported implausible "
            "punctuality %ss from %s (source=%s stop=%s)",
            active.key,
            event.vehicle_number,
            event.punctuality,
            event.event_type,
            event.source,
            event.user_stop_code,
        )
        self._invalid_journeys[active.key] = dt_util.now()
        self._active = None
        self._last_stop_progress_timestamp = None
        self.async_set_updated_data(
            BusSnapshot(
                line=LINE_PUBLIC_NUMBER,
                destination=DESTINATION,
                realtime_connected=self._kv6.connected,
            )
        )
        asyncio.create_task(
            self.async_request_refresh(),
            name="bus_57_bovenstraat_reselect_after_invalid",
        )

    async def _async_finish_active_journey(self, reason: str) -> None:
        active = self._active
        if active is None:
            return
        _LOGGER.info("Bus 57 journey %s finished (%s)", active.key, reason)
        self._passed_journeys[active.key] = dt_util.now()
        self._active = None
        self._last_stop_progress_timestamp = None
        self.async_set_updated_data(
            BusSnapshot(
                line=LINE_PUBLIC_NUMBER,
                destination=DESTINATION,
                realtime_connected=self._kv6.connected,
            )
        )
        asyncio.create_task(
            self.async_request_refresh(),
            name="bus_57_bovenstraat_next_after_end",
        )

    async def _async_apply_event(self, event: Kv6Event) -> None:
        """Apply one trusted physical-vehicle KV6 measurement."""
        active = self._active
        if active is None:
            return

        current = self.data
        if current.journey_number != active.journey_number:
            return
        if event.event_type not in _UNDERWAY_EVENTS:
            return

        # ZMQ and startup replay can deliver an older message after a newer
        # one. Never let it roll the bus or the last-passed-stop sensor back.
        if (
            event.timestamp is not None
            and current.data_timestamp is not None
            and event.timestamp < current.data_timestamp
        ):
            return

        # The event has passed Source=VEHICLE + non-zero vehicle checks, so it is
        # sufficient proof that this selected trip is physically underway.
        updated = replace(
            current,
            is_underway=True,
            realtime_connected=True,
            data_timestamp=event.timestamp or current.data_timestamp,
        )

        resolved_stop_name: str | None = None
        stop_place_code: str | None = None
        if event.user_stop_code:
            stop_place_code = self._stop_place_by_user_stop.get(event.user_stop_code)

        # DEPARTURE proves a stop was departed or passed. ONROUTE identifies
        # the last known stop and lets a fresh subscriber recover immediately
        # when the departure message happened before Home Assistant connected.
        stop_progress_event = event.event_type in {"DEPARTURE", "ONROUTE"}
        if stop_progress_event and stop_place_code:
            resolved_stop_name = await self._client.async_get_stop_name(stop_place_code)

        # Current delay is BISON KV6 Punctuality from the trusted physical bus.
        # Never expose the operator's numeric UserStopCode as a human stop name.
        if event.punctuality is not None:
            delay_source = resolved_stop_name or current.last_passed_stop
            updated = replace(
                updated,
                delay_seconds=event.punctuality,
                delay_source_stop=delay_source,
                delay_source_status=event.event_type,
                delay_observed_at=event.timestamp,
                data_timestamp=event.timestamp or updated.data_timestamp,
            )

        if stop_progress_event and event.user_stop_code:
            if not stop_place_code:
                _LOGGER.debug(
                    "No active PassengerStopAssignment for ARR UserStopCode %s; "
                    "keeping previous last passed stop",
                    event.user_stop_code,
                )
            elif stop_place_code == TARGET_STOP_PLACE_CODE:
                self._passed_journeys[active.key] = dt_util.now()
                self._active = None
                self._last_stop_progress_timestamp = None
                self.async_set_updated_data(
                    replace(
                        updated,
                        is_underway=False,
                        target_has_passed=True,
                        last_passed_stop=None,
                        last_passed_stop_code=None,
                    )
                )
                _LOGGER.info(
                    "Bus 57 journey %s passed Bovenstraat (ARR UserStopCode=%s)",
                    active.key,
                    event.user_stop_code,
                )
                asyncio.create_task(
                    self.async_request_refresh(),
                    name="bus_57_bovenstraat_next_journey",
                )
                return
            elif resolved_stop_name:
                # PassageSequenceNumber is per *same halt* in KV6, not a route
                # stop order. Reject out-of-order stop progress by the actual
                # source timestamp instead.
                is_newer = (
                    event.timestamp is None
                    or self._last_stop_progress_timestamp is None
                    or event.timestamp > self._last_stop_progress_timestamp
                )
                if is_newer:
                    updated = replace(
                        updated,
                        last_passed_stop=resolved_stop_name,
                        last_passed_stop_code=stop_place_code,
                        data_timestamp=event.timestamp or updated.data_timestamp,
                    )
                    if event.timestamp is not None:
                        self._last_stop_progress_timestamp = event.timestamp

        if updated != current:
            self.async_set_updated_data(updated)

    def _expire_journey_filters(self) -> None:
        now = dt_util.now()
        passed_cutoff = now - PASSED_JOURNEY_REMEMBER
        invalid_cutoff = now - INVALID_JOURNEY_REMEMBER
        self._passed_journeys = {
            key: seen
            for key, seen in self._passed_journeys.items()
            if seen >= passed_cutoff
        }
        self._invalid_journeys = {
            key: seen
            for key, seen in self._invalid_journeys.items()
            if seen >= invalid_cutoff
        }
