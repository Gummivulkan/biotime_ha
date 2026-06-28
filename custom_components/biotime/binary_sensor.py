"""Aggregat-Binärsensor: ist überhaupt jemand im Haus?"""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATUS_BREAK, STATUS_PRESENT
from .coordinator import BioTimeCoordinator
from .entity import BioTimeEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: BioTimeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BioTimeAnyonePresent(coordinator)])


class BioTimeAnyonePresent(BioTimeEntity, BinarySensorEntity):
    """An, sobald jemand anwesend oder in Pause ist (also im Gebäude)."""

    _attr_translation_key = "anyone_present"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(self, coordinator: BioTimeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_anyone_present"

    @property
    def is_on(self) -> bool:
        counts = self.coordinator.data["counts"]
        return (counts[STATUS_PRESENT] + counts[STATUS_BREAK]) > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            **self.coordinator.data["counts"],
            "present_names": self.coordinator.data["present_names"],
            "break_names": self.coordinator.data["break_names"],
        }
