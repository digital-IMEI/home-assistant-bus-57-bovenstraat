"""Diagnostics for Bus 57 Bovenstraat."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    ACTIVE_END_TIME,
    ACTIVE_START_TIME,
    JOURNEY_DISCOVERY_INTERVAL,
    JOURNEY_REVALIDATE_INTERVAL,
    MAINTENANCE_INTERVAL,
)
from .coordinator import Bus57Coordinator


def _serialize(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return compact diagnostics without dumping raw public-transport data."""
    coordinator: Bus57Coordinator = entry.runtime_data
    snapshot = coordinator.data
    presence = (
        hass.states.get(coordinator.presence_entity_id)
        if coordinator.presence_entity_id is not None
        else None
    )
    day_off = (
        hass.states.get(coordinator.day_off_entity_id)
        if coordinator.day_off_entity_id is not None
        else None
    )
    return {
        "line_id": coordinator.line_id,
        "bovenstraat_timing_point_code": coordinator.timing_point_code,
        "runtime": {
            "active": coordinator.runtime_active,
            "inactive_reason": coordinator.inactive_reason,
            "active_window": f"{ACTIVE_START_TIME:%H:%M}-{ACTIVE_END_TIME:%H:%M}",
            "presence_entity": coordinator.presence_entity_id,
            "presence_state": presence.state if presence is not None else None,
            "day_off_entity": coordinator.day_off_entity_id,
            "day_off_state": day_off.state if day_off is not None else None,
            "maintenance_interval_seconds": MAINTENANCE_INTERVAL.total_seconds(),
            "journey_discovery_interval_seconds": (JOURNEY_DISCOVERY_INTERVAL.total_seconds()),
            "journey_revalidate_interval_seconds": (JOURNEY_REVALIDATE_INTERVAL.total_seconds()),
        },
        "journey_selection": {
            "selected_at": _serialize(coordinator.active_selected_at),
            "last_success_at": _serialize(coordinator.last_drgl_success_at),
            "error": coordinator.selection_error,
        },
        "realtime": {
            "connected": coordinator.realtime_connected,
            "last_frame_received_at": _serialize(coordinator.last_frame_received_at),
        },
        "stop_mapping": {
            "entries": coordinator.stop_mapping_count,
            "loaded_for": _serialize(coordinator.psa_loaded_for),
            "stale": coordinator.psa_is_stale,
        },
        "snapshot": _serialize(asdict(snapshot)) if snapshot is not None else None,
    }
