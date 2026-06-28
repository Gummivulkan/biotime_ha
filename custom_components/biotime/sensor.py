"""Sensoren: Zähler je Status + Status-Sensor pro Mitarbeiter."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    STATUS_ABSENT,
    STATUS_BREAK,
    STATUS_PRESENT,
    STATUSES,
)
from .coordinator import BioTimeCoordinator
from .entity import BioTimeEntity

STATUS_ICONS = {
    STATUS_PRESENT: "mdi:account-check",
    STATUS_BREAK: "mdi:coffee",
    STATUS_ABSENT: "mdi:account-off",
}
COUNT_ICONS = {
    STATUS_PRESENT: "mdi:account-group",
    STATUS_BREAK: "mdi:coffee-outline",
    STATUS_ABSENT: "mdi:account-arrow-right",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: BioTimeCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        BioTimeCountSensor(coordinator, status) for status in STATUSES
    ]
    entities.extend(
        BioTimeEmployeeStatus(coordinator, pin)
        for pin in coordinator.data["employees"]
    )
    async_add_entities(entities)


class BioTimeCountSensor(BioTimeEntity, SensorEntity):
    """Anzahl der Mitarbeiter in einem Status."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "Personen"

    def __init__(self, coordinator: BioTimeCoordinator, status: str) -> None:
        super().__init__(coordinator)
        self._status = status
        self._attr_translation_key = f"count_{status}"
        self._attr_unique_id = f"{coordinator.serial}_count_{status}"
        self._attr_icon = COUNT_ICONS[status]

    @property
    def native_value(self) -> int:
        return self.coordinator.data["counts"][self._status]


class BioTimeEmployeeStatus(BioTimeEntity, SensorEntity):
    """Aktueller Status eines Mitarbeiters: anwesend / pause / abwesend."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUSES

    def __init__(self, coordinator: BioTimeCoordinator, pin: str) -> None:
        super().__init__(coordinator)
        self._pin = pin
        self._attr_unique_id = f"{coordinator.serial}_status_{pin}"
        self._attr_name = coordinator.data["employees"][pin]["name"]

    @property
    def _employee(self) -> dict[str, Any]:
        return self.coordinator.data["employees"].get(self._pin, {})

    @property
    def native_value(self) -> str | None:
        return self._employee.get("status")

    @property
    def icon(self) -> str:
        return STATUS_ICONS.get(self._employee.get("status"), "mdi:account-question")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        emp = self._employee
        return {
            "name": emp.get("name"),
            "pin": self._pin,
            "since": emp.get("since"),
            "last_event": emp.get("event"),
        }
