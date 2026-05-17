"""
Parser .ics
Gère les deux formats de DTSTART :
  - DTSTART:20260309T083000
  - DTSTART;TZID=Europe/Zurich:20260309T083000  ← format HEIG-VD / Google Calendar

Aidé par Claude pour ce fichier
"""
from datetime import datetime, date


def parse_ics(content: str) -> list[dict]:
    """
    Parse un fichier .ics et retourne une liste d'événements triés par date.
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
            # On compare le nom du champ sans ses paramètres (ex: "DTSTART;TZID=..." → "DTSTART")
            field = line.split(";")[0].split(":")[0].upper()
            if field == "SUMMARY":
                current["summary"] = _extract_value(line)
            elif field == "DTSTART":
                current["dtstart"] = _parse_dt(line)
            elif field == "DTEND":
                current["dtend"] = _parse_dt(line)
            elif field == "LOCATION":
                current["location"] = _extract_value(line)
            elif field == "DESCRIPTION":
                current["description"] = _extract_value(line)

    events.sort(key=lambda e: e.get("dtstart") or datetime.min)

    return [
        {
            "summary": e.get("summary", ""),
            "dtstart": e["dtstart"].isoformat() if e.get("dtstart") else None,
            "dtend":   e["dtend"].isoformat()   if e.get("dtend")   else None,
            "location": e.get("location", ""),
            "all_day": isinstance(e.get("dtstart"), date) and not isinstance(e.get("dtstart"), datetime),
        }
        for e in events
    ]


def _extract_value(line: str) -> str:
    """
    Extrait la valeur après le dernier ':' de la ligne.
    Gère les paramètres du style DTSTART;TZID=Europe/Zurich:20260309T083000
    """
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""


def _parse_dt(line: str) -> datetime | date | None:
    """
    Parse une date/heure depuis une ligne DTSTART ou DTEND.
    Supporte :
      - DTSTART:20260309T083000
      - DTSTART;TZID=Europe/Zurich:20260309T083000
      - DTSTART:20260309  (all-day)
    """
    # La valeur est toujours après le dernier ':'
    value = line.split(":")[-1].strip().replace("Z", "")
    try:
        if len(value) == 8:
            # Format YYYYMMDD → événement toute la journée
            return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        # Format YYYYMMDDTHHMMSS
        value = value.replace("T", "")
        return datetime.strptime(value[:14], "%Y%m%d%H%M%S")
    except Exception:
        return None
