#!/usr/bin/env python3
"""Standalone-Verifikation der BioTime api_v2 (reine Standardbibliothek).

Beweist Login (SHA-512) + Cookie-Auth + Anwesenheitsberechnung gegen das
echte Gerät, bevor irgendetwas in Home Assistant landet. Dieselbe Logik
wandert anschließend 1:1 in custom_components/biotime/api.py + coordinator.py.

Aufruf (Zugangsdaten als Umgebungsvariablen, niemals im Code):
    BIOTIME_HOST=192.168.1.50:8080 BIOTIME_USER=1234 BIOTIME_PASS=******** \
        python tools/test_api.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, time

# event -> Status (vgl. const.status_from_event in der Integration)
PRESENT_EVENTS = {1, 4, 5}  # Eingang, Ende Pause, Beginn Überstunden
BREAK_EVENT = 3  # Beginn Pause


def status_from_event(event):
    if event == BREAK_EVENT:
        return "pause"
    if event in PRESENT_EVENTS:
        return "anwesend"
    return "abwesend"


def _post(host: str, path: str, body: str, cookie: str | None = None) -> bytes:
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if cookie:
        headers["Cookie"] = f"ZKTECOKEY={cookie}"
    req = urllib.request.Request(
        f"http://{host}/{path}", data=body.encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def _get(host: str, path: str, cookie: str) -> bytes:
    req = urllib.request.Request(
        f"http://{host}/{path}", headers={"Cookie": f"ZKTECOKEY={cookie}"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def login(host: str, user: str, password: str) -> str:
    pw_hash = hashlib.sha512(password.encode()).hexdigest()
    body = f"username={user}&password={pw_hash}"
    data = json.loads(_post(host, "api_v2/authentication", body))
    if not data.get("success"):
        raise RuntimeError(f"Login fehlgeschlagen: {data.get('message')}")
    return data["token"]


def day_range_ms(day: datetime) -> tuple[int, int]:
    """Start/Ende des lokalen Tages als Unix-ms (wie Date.getTime() im Web-UI)."""
    start = datetime.combine(day.date(), time(0, 0, 0)).astimezone()
    end = datetime.combine(day.date(), time(23, 59, 59)).astimezone()
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def fetch_today(host: str, cookie: str) -> list[dict]:
    start_ms, end_ms = day_range_ms(datetime.now())
    body = (
        f"start_date={start_ms}&last_date={end_ms}"
        "&is_special=true&is_photo=false&page=-1"
    )
    data = json.loads(_post(host, "api_v2/attendances", body, cookie))
    return data.get("values", [])


def _latest_punch(record: dict) -> dict | None:
    """Letzter aktiver Stempel des Tages (Sortierung über day+date)."""
    active = [p for p in record.get("attendances", []) if p.get("is_active")]
    if not active:
        return None
    return max(active, key=lambda p: f"{p['day']} {p['date']}")


def compute_status(host: str, cookie: str) -> dict:
    roster = json.loads(_get(host, "api_v2/employees", cookie)).get("values", [])
    employees = {e["code"]: {"name": e["name"], "status": "abwesend", "since": None}
                 for e in roster}

    for record in fetch_today(host, cookie):
        punch = _latest_punch(record)
        if not punch:
            continue
        employees[record["pin"]] = {
            "name": record["name"],
            "status": status_from_event(punch["event"]),
            "since": punch["date"],
        }

    counts = {"anwesend": 0, "pause": 0, "abwesend": 0}
    for emp in employees.values():
        counts[emp["status"]] += 1

    return {"counts": counts, "employees": employees}


def main() -> int:
    host = os.environ.get("BIOTIME_HOST")
    user = os.environ.get("BIOTIME_USER")
    password = os.environ.get("BIOTIME_PASS")
    if not (host and user and password):
        print("Bitte BIOTIME_HOST, BIOTIME_USER, BIOTIME_PASS setzen.", file=sys.stderr)
        return 2

    try:
        token = login(host, user, password)
        result = compute_status(host, token)
    except (urllib.error.URLError, RuntimeError) as err:
        print(f"FEHLER: {err}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
