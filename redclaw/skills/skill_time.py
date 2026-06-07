from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

SKILL = {
    "name": "time",
    "description": "Gibt Datum und Uhrzeit für Berlin aus.",
    "permissions": [],
    "enabled": True,
}


def run(query, context):
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    return f"Es ist {now:%H:%M Uhr} am {now:%d.%m.%Y}."
