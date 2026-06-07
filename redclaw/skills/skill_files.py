from __future__ import annotations

from pathlib import Path

SKILL = {
    "name": "files",
    "description": "Liest und durchsucht Dateien in freigegebenen Ordnern.",
    "permissions": ["file_read", "file_write"],
    "enabled": True,
}


def run(query, context):
    parts = query.split(maxsplit=2)
    if len(parts) < 2:
        return "Datei-Skill: nutze `datei lies <pfad>`, `datei suche <text>` oder `datei schreibe <pfad> :: <text>`."
    action = parts[1].lower()
    value = parts[2] if len(parts) > 2 else ""
    if action in {"lies", "read"}:
        path = Path(value)
        decision = context.permissions.check_path(path)
        if decision.needs_confirmation:
            context.logger.log("warn", "security", "Dateizugriff braucht Bestaetigung", {"path": str(path), "reason": decision.reason})
            return f"Dafuer brauche ich erst deine Freigabe: {decision.reason}"
        if not path.exists() or not path.is_file():
            return "Diese Datei finde ich nicht."
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:4000] if text else "Die Datei ist leer."
    if action in {"suche", "search"}:
        needle = value.lower()
        matches = []
        for root in context.settings.allowed_paths:
            for path in Path(root).rglob("*"):
                if path.is_file() and path.stat().st_size < 1_000_000:
                    try:
                        content = path.read_text(encoding="utf-8", errors="ignore").lower()
                    except Exception:
                        continue
                    if needle in content or needle in path.name.lower():
                        matches.append(str(path))
                if len(matches) >= 20:
                    break
        return "Treffer:\n" + "\n".join(matches) if matches else "Keine lokalen Treffer gefunden."
    if action in {"schreibe", "write"}:
        if "::" not in value:
            return "Nutze `datei schreibe <pfad> :: <text>`."
        raw_path, content = value.split("::", 1)
        path = Path(raw_path.strip())
        decision = context.permissions.check_path(path)
        if decision.needs_confirmation:
            context.logger.log("warn", "security", "Datei-Schreibzugriff braucht Bestaetigung", {"path": str(path), "reason": decision.reason})
            return f"Dafuer brauche ich erst deine Freigabe: {decision.reason}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip(), encoding="utf-8")
        context.logger.log("info", "file", "Datei geschrieben", {"path": str(path)})
        return f"Datei geschrieben: {path}"
    return "Diese Datei-Aktion kenne ich noch nicht."
