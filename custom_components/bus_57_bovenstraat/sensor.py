"""Sensors for Bus 57 Bovenstraat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DESTINATION, DOMAIN, LINE_PUBLIC_NUMBER
from .coordinator import Bus57Coordinator
from .models import BusSnapshot


@dataclass(frozen=True, kw_only=True)
class Bus57SensorDescription(SensorEntityDescription):
    """Describe a Bus 57 sensor."""

    value_fn: Callable[[BusSnapshot], object | None]
    attrs_fn: Callable[[BusSnapshot], dict[str, object]] | None = None


def _delay_minutes(data: BusSnapshot) -> float | None:
    if data.delay_seconds is None:
        return None
    return round(data.delay_seconds / 60, 1)


def _delay_attrs(data: BusSnapshot) -> dict[str, object]:
    attrs: dict[str, object] = {
        "is_underway": data.is_underway,
        "realtime_connected": data.realtime_connected,
    }
    if data.delay_seconds is not None:
        attrs["delay_seconds"] = data.delay_seconds
    if data.delay_source_stop:
        attrs["source_stop"] = data.delay_source_stop
    if data.delay_source_status:
        attrs["source_status"] = data.delay_source_status
    if data.delay_observed_at:
        attrs["observed_at"] = data.delay_observed_at.isoformat()
    if data.journey_number is not None:
        attrs["journey_number"] = data.journey_number
    if data.journey_key:
        attrs["journey_key"] = data.journey_key
    return attrs


SENSORS: tuple[Bus57SensorDescription, ...] = (
    Bus57SensorDescription(
        key="delay",
        translation_key="delay",
        icon="mdi:bus-clock",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=1,
        value_fn=_delay_minutes,
        attrs_fn=_delay_attrs,
    ),
    Bus57SensorDescription(
        key="last_passed_stop",
        translation_key="last_passed_stop",
        icon="mdi:bus-stop",
        value_fn=lambda data: data.last_passed_stop,
    ),
    Bus57SensorDescription(
        key="scheduled_bovenstraat",
        translation_key="scheduled_bovenstraat",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.target_scheduled_time,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Bus 57 sensors."""
    coordinator: Bus57Coordinator = entry.runtime_data
    async_add_entities(Bus57Sensor(coordinator, description) for description in SENSORS)


class Bus57Sensor(CoordinatorEntity[Bus57Coordinator], SensorEntity):
    """A sensor backed by the shared Bus 57 coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Bus57Coordinator,
        description: Bus57SensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"arriva_57_maastricht_bovenstraat_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "arriva_57_maastricht_bovenstraat_noorbeek")},
            name=f"Bus {LINE_PUBLIC_NUMBER} → {DESTINATION} · Bovenstraat",
            manufacturer="Arriva / NDOV",
            model="Realtime NDOV KV6",
        )

    @property
    def available(self) -> bool:
        """Expose values only while an actual bus is running."""
        return super().available and self.coordinator.data.is_underway

    @property
    def native_value(self) -> object | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        if self.entity_description.attrs_fn is None:
            return None
        attrs = self.entity_description.attrs_fn(self.coordinator.data)
        if self.coordinator.timing_point_code:
            attrs["bovenstraat_tpc"] = self.coordinator.timing_point_code
        if self.coordinator.line_id:
            attrs["ndov_line_id"] = self.coordinator.line_id
        return attrs
