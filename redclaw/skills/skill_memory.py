from __future__ import annotations

from datetime import datetime, timedelta
import re

SKILL = {
    "name": "memory",
    "description": "Liest Memory und legt einfache Erinnerungen an.",
    "permissions": ["memory"],
    "enabled": True,
}


def run(query, context):
    lowered = query.lower()
    if "erinnere mich" in lowered:
        minutes = 10
        minute_match = re.search(r"in (\d+) minuten?", lowered)
        if minute_match:
            minutes = int(minute_match.group(1))
        text = re.sub(r".*?an ", "", query, flags=re.IGNORECASE).strip() or query
        due = datetime.utcnow() + timedelta(minutes=minutes)
        context.memory.conn.execute(
            "INSERT INTO reminders(text, due_at, channel) VALUES (?, ?, ?)",
            (text, due.isoformat(), "discord"),
        )
        context.memory.conn.commit()
        context.memory.save("reminders", f"reminder:{text[:40].lower()}", f"{text} um {due.isoformat()}", source=context.source)
        return f"Erinnerung gespeichert: {text} in {minutes} Minuten."
    if "was weißt" in lowered or "was weisst" in lowered:
        items = context.memory.all(limit=50)
        return "\n".join(f"- [{item.category}] {item.value}" for item in items) if items else "Noch nichts gespeichert."
    items = context.memory.search(query, limit=10)
    return "\n".join(f"- [{item.category}] {item.value}" for item in items) if items else "Kein Memory-Treffer."
