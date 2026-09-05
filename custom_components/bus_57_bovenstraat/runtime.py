"""Pure runtime policy helpers for Bus 57 Bovenstraat."""

from __future__ import annotations

from datetime import datetime

from .const import ACTIVE_END_TIME, ACTIVE_START_TIME, MAX_EARLY_SECONDS

TRIP_START_EVENTS = frozenset({"DEPARTURE", "ONROUTE"})


def runtime_inactive_reason(
    now: datetime,
    presence_state: str | None,
    day_off_state: str | None,
) -> str | None:
    """Return why the integration must sleep, or ``None`` when it may run."""
    local_clock = now.timetz().replace(tzinfo=None)
    if not ACTIVE_START_TIME <= local_clock < ACTIVE_END_TIME:
        return "outside_time_window"
    if now.weekday() >= 5:
        return "weekend"
    if presence_state != "home":
        return "not_home"
    if day_off_state == "on":
        return "day_off"
    if day_off_state != "off":
        return "day_off_state_unknown"
    return None


def should_reject_implausibly_early(
    event_type: str,
    punctuality: int | None,
    *,
    trip_underway: bool,
) -> bool:
    """Reject a >10 minute lead only once an event proves trip progress."""
    return (
        punctuality is not None
        and punctuality < -MAX_EARLY_SECONDS
        and (trip_underway or event_type in TRIP_START_EVENTS)
    )
