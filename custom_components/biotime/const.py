"""Konstanten der BioTime-Integration."""
from __future__ import annotations

DOMAIN = "biotime"

DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 60  # Sekunden

CONF_USERCODE = "usercode"

# event-IDs laut /api_v2/attendanceEvents.
PRESENT_EVENTS: set[int] = {1, 4, 5}  # Eingang, Ende Pause, Beginn Überstunden
BREAK_EVENT: int = 3  # Beginn Pause
EVENT_NAMES: dict[int, str] = {
    1: "Eingang",
    2: "Ausgang",
    3: "Beginn Pause",
    4: "Ende Pause",
    5: "Beginn Überstunden",
    6: "Ende Überstunden",
}

# Anwesenheitsstatus (Werte = Sensor-States)
STATUS_PRESENT = "anwesend"
STATUS_BREAK = "pause"
STATUS_ABSENT = "abwesend"
STATUSES: list[str] = [STATUS_PRESENT, STATUS_BREAK, STATUS_ABSENT]


def status_from_event(event: int | None) -> str:
    """Letzter Stempel-Event -> Anwesenheitsstatus."""
    if event == BREAK_EVENT:
        return STATUS_BREAK
    if event in PRESENT_EVENTS:
        return STATUS_PRESENT
    return STATUS_ABSENT
