"""Small HTTP client for timetable, PSA stop mapping and stop names."""

from __future__ import annotations

import asyncio
from datetime import date, datetime
import gzip

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    DATA_OWNER,
    DRGL_BASE_URL,
    DRGL_TARGET_STOP_AREA,
    NDOV_HALTES_BASE_URL,
    PSA_INDEX_URL,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)
from .models import (
    AMSTERDAM,
    JourneySelection,
    ParseError,
    parse_drgl_departures,
    parse_drgl_stop_name,
    parse_passenger_stop_assignments,
    select_latest_psa_filename,
)


class TransitHttpError(Exception):
    """HTTP or public-data source failed."""


class TransitHttpClient:
    """Fetch the small HTTP resources used beside the realtime KV6 stream."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._timeout = ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
        self._headers = {
            "User-Agent": USER_AGENT,
            "Cache-Control": "no-cache",
        }
        self._stop_name_cache: dict[str, str | None] = {}
        self._psa_mapping: dict[str, str] | None = None
        self._psa_loaded_for: date | None = None
        self._psa_filename: str | None = None

    async def _get_text_url(self, url: str) -> str:
        try:
            async with self._session.get(
                url,
                headers={**self._headers, "Accept": "text/html,application/xhtml+xml"},
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                return await response.text()
        except (ClientError, TimeoutError, UnicodeError) as err:
            raise TransitHttpError(f"GET {url} failed: {err}") from err

    async def _get_bytes_url(self, url: str) -> bytes:
        try:
            async with self._session.get(
                url,
                headers={**self._headers, "Accept": "application/gzip,application/octet-stream,*/*"},
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                return await response.read()
        except (ClientError, TimeoutError) as err:
            raise TransitHttpError(f"GET {url} failed: {err}") from err

    async def async_get_bovenstraat_journeys(self) -> list[JourneySelection]:
        """Return journeys shown at Bovenstraat towards Maastricht."""
        html = await self._get_text_url(f"{DRGL_BASE_URL}/stop/{DRGL_TARGET_STOP_AREA}")
        return parse_drgl_departures(html)

    async def async_get_passenger_stop_assignments(self) -> dict[str, str]:
        """Return today's official ARR UserStopCode -> CHB StopPlaceCode map.

        The NDOV PassengerStopAssignment export is about 1 MB compressed and is
        downloaded at most once per local calendar day per HA process. Parsing
        and gzip decompression run off the Home Assistant event loop.
        """
        today = datetime.now(AMSTERDAM).date()
        if self._psa_mapping is not None and self._psa_loaded_for == today:
            return self._psa_mapping

        try:
            index_html = await self._get_text_url(PSA_INDEX_URL)
            filename = select_latest_psa_filename(index_html, today)
            if not filename:
                raise TransitHttpError("No PassengerStopAssignment export found in NDOV index")

            payload = await self._get_bytes_url(f"{NDOV_HALTES_BASE_URL}/{filename}")

            def decode_and_parse() -> dict[str, str]:
                # A .gz file normally arrives as gzip bytes. Be tolerant of an
                # HTTP intermediary that has already decoded Content-Encoding.
                xml_bytes = gzip.decompress(payload) if payload[:2] == b"\x1f\x8b" else payload
                return parse_passenger_stop_assignments(
                    xml_bytes,
                    data_owner=DATA_OWNER,
                    valid_on=today,
                )

            mapping = await asyncio.to_thread(decode_and_parse)
            if not mapping:
                raise TransitHttpError(
                    f"PassengerStopAssignment {filename} contains no active {DATA_OWNER} mappings"
                )

        except (OSError, ParseError) as err:
            # Keep a previously working map if a daily refresh is temporarily bad.
            if self._psa_mapping is not None:
                return self._psa_mapping
            raise TransitHttpError(f"PassengerStopAssignment parsing failed: {err}") from err
        except TransitHttpError:
            if self._psa_mapping is not None:
                return self._psa_mapping
            raise

        self._psa_mapping = mapping
        self._psa_loaded_for = today
        self._psa_filename = filename
        return mapping

    @property
    def psa_filename(self) -> str | None:
        """Return the currently loaded PSA export filename for diagnostics."""
        return self._psa_filename

    async def async_get_stop_name(self, stop_place_code: str) -> str | None:
        """Resolve a NATIONAL CHB StopPlaceCode to a human-readable name.

        This method deliberately does not accept/fallback to a KV6 UserStopCode.
        Those codes live in the operator's own domain and first have to be
        normalized through PassengerStopAssignment.
        """
        if stop_place_code in self._stop_name_cache:
            return self._stop_name_cache[stop_place_code]

        try:
            # PassengerStopAssignment already returns the complete national
            # identifier (for example ``NL:S:66420180``).
            html = await self._get_text_url(f"{DRGL_BASE_URL}/stop/{stop_place_code}")
        except TransitHttpError:
            self._stop_name_cache[stop_place_code] = None
            return None

        name = parse_drgl_stop_name(html)
        self._stop_name_cache[stop_place_code] = name
        return name
