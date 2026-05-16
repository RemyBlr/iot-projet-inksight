"""
Parser .ics minimal
Aidé par Claude pour ce fichier
"""
from datetime import datetime, date


def parse_ics(content: str) -> list[dict]:
    """
    Parse un fichier .ics et retourne une liste d'événements triés
    """
    events = []
    current = {}
    in_event = False

    for line in content.splitlines():
        line = line.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
            current = {}
        elif line == "END:VEVENT":
            in_event = False
            if "summary" in current and "dtstart" in current:
                events.append(current)
        elif in_event:
            if line.startswith("SUMMARY"):
                current["summary"] = _extract_value(line)
            elif line.startswith("DTSTART"):
                current["dtstart"] = _parse_dt(line)
            elif line.startswith("DTEND"):
                current["dtend"] = _parse_dt(line)
            elif line.startswith("LOCATION"):
                current["location"] = _extract_value(line)
            elif line.startswith("DESCRIPTION"):
                current["description"] = _extract_value(line)

    # Trier par date de début
    events.sort(key=lambda e: e.get("dtstart") or datetime.min)

    # Convertir en dicts JSON-sérialisables
    return [
        {
            "summary": e.get("summary", ""),
            "dtstart": e["dtstart"].isoformat() if e.get("dtstart") else None,
            "dtend": e["dtend"].isoformat() if e.get("dtend") else None,
            "location": e.get("location", ""),
            "all_day": isinstance(e.get("dtstart"), date) and not isinstance(e.get("dtstart"), datetime),
        }
        for e in events
    ]


def _extract_value(line: str) -> str:
    """
    Extrait la valeur après le premier ':' ou ';...:'
    """
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""


def _parse_dt(line: str) -> datetime | date | None:
    value = _extract_value(line)
    try:
        if len(value) == 8:  # YYYYMMDD — all day
            return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        # YYYYMMDDTHHMMSS ou YYYYMMDDTHHMMSSZ
        value = value.replace("Z", "").replace("T", "")
        return datetime.strptime(value[:14], "%Y%m%d%H%M%S")
    except Exception:
        return None
