"""Gemeinsame Basis-Entity mit Geräte-Zuordnung."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BioTimeCoordinator


class BioTimeEntity(CoordinatorEntity[BioTimeCoordinator]):
    """Basis: hängt alle Entities an ein gemeinsames BioTime-Gerät."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BioTimeCoordinator) -> None:
        super().__init__(coordinator)
        terminal = coordinator.terminal
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.serial)},
            name="BioTime",
            manufacturer="ZKTeco / WebServerZK",
            model=f"Firmware {terminal.get('firmwareVersion', '?')}",
            sw_version=terminal.get("webserverVersion"),
            serial_number=coordinator.serial,
            configuration_url=coordinator.api.base_url,
        )
