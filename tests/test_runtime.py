"""Tests for the lightweight morning runtime policy."""

from __future__ import annotations

from datetime import datetime

import pytest

from custom_components.bus_57_bovenstraat.models import AMSTERDAM
from custom_components.bus_57_bovenstraat.runtime import (
    runtime_inactive_reason,
    should_reject_implausibly_early,
)


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    (
        (5, 59, "outside_time_window"),
        (6, 0, None),
        (9, 59, None),
        (10, 0, "outside_time_window"),
    ),
)
def test_runtime_boundaries(hour: int, minute: int, expected: str | None) -> None:
    now = datetime(2026, 8, 31, hour, minute, tzinfo=AMSTERDAM)
    assert runtime_inactive_reason(now, "home", "off") == expected


@pytest.mark.parametrize(
    ("year", "month", "day", "expected"),
    (
        (2026, 9, 4, None),
        (2026, 9, 5, "weekend"),
        (2026, 9, 6, "weekend"),
        (2026, 9, 7, None),
    ),
)
def test_runtime_only_runs_monday_through_friday(
    year: int,
    month: int,
    day: int,
    expected: str | None,
) -> None:
    now = datetime(year, month, day, 7, 0, tzinfo=AMSTERDAM)
    assert runtime_inactive_reason(now, "home", "off") == expected


@pytest.mark.parametrize(
    ("presence", "day_off", "expected"),
    (
        ("not_home", "off", "not_home"),
        (None, "off", "not_home"),
        ("home", "on", "day_off"),
        ("home", "unknown", "day_off_state_unknown"),
        ("home", None, "day_off_state_unknown"),
    ),
)
def test_runtime_requires_home_and_a_workday(
    presence: str | None,
    day_off: str | None,
    expected: str,
) -> None:
    now = datetime(2026, 8, 31, 7, 0, tzinfo=AMSTERDAM)
    assert runtime_inactive_reason(now, presence, day_off) == expected


@pytest.mark.parametrize("event_type", ("ARRIVAL", "ONSTOP"))
def test_waiting_at_origin_is_not_rejected_or_exposed(event_type: str) -> None:
    assert not should_reject_implausibly_early(
        event_type,
        -900,
        trip_underway=False,
    )


@pytest.mark.parametrize("event_type", ("DEPARTURE", "ONROUTE"))
def test_trip_start_can_reject_implausible_early_data(event_type: str) -> None:
    assert should_reject_implausibly_early(
        event_type,
        -901,
        trip_underway=False,
    )


def test_early_guard_applies_after_trip_started() -> None:
    assert should_reject_implausibly_early(
        "ONSTOP",
        -901,
        trip_underway=True,
    )
    assert not should_reject_implausibly_early(
        "ONROUTE",
        -600,
        trip_underway=True,
    )
