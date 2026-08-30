"""Diagnostics for Bus 57 Bovenstraat."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import Bus57Coordinator


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return compact diagnostics without dumping raw OVapi responses."""
    coordinator: Bus57Coordinator = entry.runtime_data
    snapshot = coordinator.data
    return {
        "line_id": coordinator.line_id,
        "bovenstraat_timing_point_code": coordinator.timing_point_code,
        "realtime_connected": coordinator.realtime_connected,
        "selection_error": coordinator.selection_error,
        "update_interval_seconds": (
            coordinator.update_interval.total_seconds() if coordinator.update_interval else None
        ),
        "snapshot": _serialize(asdict(snapshot)) if snapshot is not None else None,
    }
