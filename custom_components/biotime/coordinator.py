"""DataUpdateCoordinator: pollt BioTime und berechnet Anwesenheitsstatus."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .api import BioTimeApi, BioTimeAuthError, BioTimeConnectionError
from .const import (
    DOMAIN,
    EVENT_NAMES,
    STATUS_ABSENT,
    STATUS_BREAK,
    STATUS_PRESENT,
    STATUSES,
    status_from_event,
)

_LOGGER = logging.getLogger(__name__)


def _latest_active_punch(record: dict[str, Any]) -> dict[str, Any] | None:
    """Letzter aktiver Stempel des Tages (Sortierung über day + date)."""
    active = [p for p in record.get("attendances", []) if p.get("is_active")]
    if not active:
        return None
    return max(active, key=lambda p: f"{p.get('day', '')} {p.get('date', '')}")


class BioTimeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Hält Terminal-Info, Mitarbeiterliste und aktuellen Anwesenheitsstatus."""

    def __init__(self, hass: HomeAssistant, api: BioTimeApi, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.terminal: dict[str, Any] = {}

    @property
    def serial(self) -> str:
        return self.terminal.get("serial") or "unknown"

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if not self.terminal:
                self.terminal = await self.api.async_get_terminal_info()

            roster = await self.api.async_get_employees()
            now = dt_util.now()
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            records = await self.api.async_get_attendances(
                int(start.timestamp() * 1000), int(end.timestamp() * 1000)
            )
        except BioTimeAuthError as err:
            # löst den HA-Reauth-Flow aus (z. B. wenn das Terminal-Passwort geändert wurde)
            raise ConfigEntryAuthFailed(f"Authentifizierung fehlgeschlagen: {err}") from err
        except BioTimeConnectionError as err:
            raise UpdateFailed(f"Gerät nicht erreichbar: {err}") from err

        # pin -> letzter Stempel des heutigen Tages
        detail: dict[str, dict[str, Any]] = {}
        for record in records:
            punch = _latest_active_punch(record)
            event = punch.get("event") if punch else None
            detail[record["pin"]] = {
                "name": record.get("name", record["pin"]),
                "status": status_from_event(event),
                "since": punch.get("date") if punch else None,
                "event": EVENT_NAMES.get(event) if event else None,
            }

        # Vollständige Mitarbeiterliste (auch Abwesende) für stabile Entities.
        # Annahme (verifiziert für dieses Gerät): die Mitarbeiter-Kennung ist in
        # beiden Endpunkten identisch – Roster liefert sie als `code`, Stempel als
        # `pin`. Sollte ein Gerät hier je getrennte Namensräume verwenden, landen
        # Gestempelte im setdefault-Zweig unten (separate Entity statt Merge).
        employees: dict[str, dict[str, Any]] = {}
        for emp in roster:
            pin = emp.get("code")
            if not pin:
                continue
            info = detail.get(pin)
            employees[pin] = info or {
                "name": emp.get("name", pin),
                "status": STATUS_ABSENT,
                "since": None,
                "event": None,
            }
            employees[pin]["name"] = emp.get("name", employees[pin]["name"])
        # Gestempelte, die (theoretisch) nicht im Roster stehen, nachtragen
        for pin, info in detail.items():
            employees.setdefault(pin, info)

        counts = {status: 0 for status in STATUSES}
        for emp in employees.values():
            counts[emp["status"]] += 1

        return {
            "employees": employees,
            "counts": counts,
            "present_names": sorted(
                e["name"] for e in employees.values() if e["status"] == STATUS_PRESENT
            ),
            "break_names": sorted(
                e["name"] for e in employees.values() if e["status"] == STATUS_BREAK
            ),
        }
