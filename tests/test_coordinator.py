"""Focused tests for physical bus-position event handling."""

from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.bus_57_bovenstraat.coordinator import Bus57Coordinator
from custom_components.bus_57_bovenstraat.models import (
    BusSnapshot,
    JourneySelection,
    Kv6Event,
)


class _StopNameClient:
    def get_cached_stop_name(self, stop_place_code: str) -> str | None:
        return "Busstation, Gulpen" if stop_place_code == "NL:S:origin" else None


def _event(event_type: str, punctuality: int) -> Kv6Event:
    observed = datetime(2026, 8, 31, 6, 30, tzinfo=UTC)
    return Kv6Event(
        event_type=event_type,
        data_owner_code="ARR",
        line_planning_number="26057",
        operating_day="2026-08-31",
        journey_number=123,
        reinforcement_number=0,
        user_stop_code="origin",
        passage_sequence_number=1,
        timestamp=observed,
        source="VEHICLE",
        punctuality=punctuality,
        vehicle_number="42",
        received_at=observed,
    )


def _coordinator() -> Bus57Coordinator:
    coordinator: Any = object.__new__(Bus57Coordinator)
    coordinator._active = JourneySelection(123, "2026-08-31", None)
    coordinator._runtime_active = True
    coordinator._last_event_order_timestamp = None
    coordinator._last_stop_progress_timestamp = None
    coordinator._stop_place_by_user_stop = {"origin": "NL:S:origin"}
    coordinator._client = _StopNameClient()
    coordinator._schedule_stop_name_resolution = lambda *_: None
    coordinator.data = BusSnapshot(
        journey_number=123,
        operating_day="2026-08-31",
        journey_key=coordinator._active.key,
        runtime_active=True,
    )
    coordinator.async_set_updated_data = lambda data: setattr(coordinator, "data", data)
    return coordinator


@pytest.mark.asyncio
async def test_waiting_at_origin_sets_position_but_not_delay() -> None:
    coordinator = _coordinator()

    await coordinator._async_apply_event(_event("ONSTOP", -600))

    assert coordinator.data.current_stop == "Busstation, Gulpen"
    assert coordinator.data.current_stop_code == "NL:S:origin"
    assert not coordinator.data.is_underway
    assert coordinator.data.delay_seconds is None


@pytest.mark.asyncio
async def test_departure_advances_position_and_starts_delay() -> None:
    coordinator = _coordinator()
    coordinator.data = BusSnapshot(
        journey_number=123,
        operating_day="2026-08-31",
        journey_key=coordinator._active.key,
        runtime_active=True,
        current_stop="Busstation, Gulpen",
        current_stop_code="NL:S:origin",
        last_journey_cancelled=True,
    )

    await coordinator._async_apply_event(_event("DEPARTURE", -72))

    assert coordinator.data.current_stop is None
    assert coordinator.data.last_passed_stop == "Busstation, Gulpen"
    assert coordinator.data.is_underway
    assert coordinator.data.delay_seconds == -72
    assert not coordinator.data.last_journey_cancelled
