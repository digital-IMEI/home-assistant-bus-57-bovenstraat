"""Tests for lightweight sensor state selection."""

from datetime import UTC, datetime

from custom_components.bus_57_bovenstraat.const import (
    JOURNEY_STATUS_CANCELLED,
    JOURNEY_STATUS_NO_BUS,
    JOURNEY_STATUS_PREVIOUS_CANCELLED,
    JOURNEY_STATUS_REALTIME_UNAVAILABLE,
    JOURNEY_STATUS_UNDERWAY,
    JOURNEY_STATUS_WAITING,
)
from custom_components.bus_57_bovenstraat.models import BusSnapshot
from custom_components.bus_57_bovenstraat.sensor import (
    NO_BUS_UNDERWAY,
    NOT_DEPARTED,
    _status_attrs,
    journey_status,
    position_value,
)


def test_position_prefers_current_stop_then_last_passed_stop() -> None:
    assert (
        position_value(BusSnapshot(current_stop="Busstation, Gulpen", last_passed_stop="Wittem"))
        == "Busstation, Gulpen"
    )
    assert position_value(BusSnapshot(last_passed_stop="Wittem")) == "Wittem"


def test_position_has_stable_waiting_and_no_bus_fallbacks() -> None:
    assert position_value(BusSnapshot(journey_number=123)) == NOT_DEPARTED
    assert position_value(BusSnapshot()) == NO_BUS_UNDERWAY


def test_journey_status_states() -> None:
    assert journey_status(BusSnapshot()) == JOURNEY_STATUS_NO_BUS
    assert journey_status(BusSnapshot(journey_number=123)) == JOURNEY_STATUS_WAITING
    assert journey_status(BusSnapshot(is_underway=True)) == JOURNEY_STATUS_UNDERWAY
    assert (
        journey_status(BusSnapshot(is_underway=True, realtime_stale=True))
        == JOURNEY_STATUS_REALTIME_UNAVAILABLE
    )
    assert journey_status(BusSnapshot(last_journey_cancelled=True)) == JOURNEY_STATUS_CANCELLED
    assert (
        journey_status(BusSnapshot(journey_number=456, last_journey_cancelled=True))
        == JOURNEY_STATUS_PREVIOUS_CANCELLED
    )


def test_journey_status_exposes_cancelled_scheduled_time() -> None:
    cancelled_time = datetime(2026, 9, 3, 5, 41, tzinfo=UTC)

    assert (
        _status_attrs(
            BusSnapshot(
                journey_number=456,
                last_journey_cancelled=True,
                cancelled_scheduled_time=cancelled_time,
            )
        )["cancelled_scheduled_time"]
        == "2026-09-03T05:41:00+00:00"
    )
