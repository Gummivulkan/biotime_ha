# BioTime Anwesenheit – Home Assistant Integration

Bindet ein eigenständiges **BioTime / WebServerZK** Zeiterfassungsterminal (ZKTeco-basiert,
eingebettete `api_v2`-Weboberfläche) in Home Assistant ein und stellt die **Anwesenheit**
der Mitarbeiter als Entities bereit – z. B. um Heizung und Licht anhand eingestempelter
Mitarbeiter zu steuern.

Reines **local polling**, keine Cloud, kein MQTT, keine externen Abhängigkeiten.

## Entities

| Entity | Typ | Beschreibung |
|---|---|---|
| `sensor.biotime_<name>` | enum | Ein Sensor **pro Mitarbeiter**: `anwesend` / `pause` / `abwesend`. Attribute: `name`, `pin`, `since`, `last_event` |
| `sensor.biotime_anwesend` | measurement | Anzahl anwesender Mitarbeiter |
| `sensor.biotime_in_pause` | measurement | Anzahl Mitarbeiter in Pause |
| `sensor.biotime_abwesend` | measurement | Anzahl abwesender Mitarbeiter |
| `binary_sensor.biotime_jemand_im_haus` | occupancy | An, sobald jemand **anwesend oder in Pause** ist. Attribute: Zähler je Status + Namenslisten |

**Status-Logik:** Pro Mitarbeiter wird der *letzte aktive Stempel des heutigen Tages*
ausgewertet. `Eingang` / `Ende Pause` / `Beginn Überstunden` → **anwesend**;
`Beginn Pause` → **pause**; `Ausgang` / `Ende Überstunden` / kein Stempel → **abwesend**.

Ein fertiges Dashboard (Anwesend / Pause / Abwesend, live gruppiert) liegt unter
[`dashboard/biotime-dashboard.yaml`](dashboard/biotime-dashboard.yaml).

## Installation (HACS)

1. HACS → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/Gummivulkan/biotime_ha`, Kategorie **Integration**.
2. „BioTime Anwesenheit" installieren, Home Assistant **neu starten**.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → BioTime**.
4. Host (IP/Hostname des Terminals, z. B. `192.168.1.50`), Port (`8080`),
   **Usercode + Passwort** eingeben (dieselben wie beim Web-Login des Geräts).

### Manuell (ohne HACS)
`custom_components/biotime/` nach `<config>/custom_components/biotime/` kopieren, neu starten.

## Beispiel-Automationen

Heizung/Licht an, wenn der Erste kommt – aus, wenn der Letzte geht:

```yaml
automation:
  - alias: "Werkstatt: Licht an wenn jemand im Haus"
    trigger:
      - platform: state
        entity_id: binary_sensor.biotime_jemand_im_haus
        to: "on"
    action:
      - service: light.turn_on
        target: { entity_id: light.werkstatt }

  - alias: "Heizung absenken wenn niemand mehr da"
    trigger:
      - platform: state
        entity_id: binary_sensor.biotime_jemand_im_haus
        to: "off"
        for: "00:10:00"
    action:
      - service: climate.set_temperature
        target: { entity_id: climate.werkstatt }
        data: { temperature: 16 }
```

Personenbezogen (nur wenn ein bestimmter Mitarbeiter anwesend ist – Entity-Namen anpassen):

```yaml
  - alias: "Büro heizen wenn Mitarbeiter da"
    trigger:
      - platform: state
        entity_id: sensor.biotime_max_mustermann
        to: "anwesend"
    action:
      - service: climate.set_temperature
        target: { entity_id: climate.buero }
        data: { temperature: 21 }
```

## Optionen

Abfrageintervall (Standard 60 s) unter **Geräte & Dienste → BioTime → Konfigurieren**.

## Test ohne Home Assistant

`tools/test_api.py` prüft Login + Anwesenheitsberechnung gegen das echte Gerät
(reine Standardbibliothek):

```bash
BIOTIME_HOST=192.168.1.50:8080 BIOTIME_USER=1234 BIOTIME_PASS=******** \
  python tools/test_api.py
```

## Technische Details

- Login: `POST /api_v2/authentication`, Passwort als **SHA-512-Hex**, Antwort liefert `token`.
- Folge-Requests authentifizieren über Cookie **`ZKTECOKEY=<token>`**; bei `401` wird automatisch neu eingeloggt.
- Stempel: `POST /api_v2/attendances` mit `start_date`/`last_date` als **Unix-Timestamp in Millisekunden**
  (Datums-Strings lassen den eingebetteten Server abstürzen).

## Haftung

Inoffizielle Integration, kein Bezug zu ZKTeco. Nutzung auf eigene Verantwortung.
