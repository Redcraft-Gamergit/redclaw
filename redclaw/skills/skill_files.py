from __future__ import annotations

from pathlib import Path
import re
import time
import zipfile


ATTACH_MARKER = "__REDCLAW_ATTACH__:"
MAX_DISCORD_ATTACHMENT_BYTES = 24 * 1024 * 1024

SKILL = {
    "name": "files",
    "description": "Liest und durchsucht Dateien in freigegebenen Ordnern.",
    "permissions": ["file_read", "file_write"],
    "enabled": True,
}


def run(query, context):
    query = _normalize_query(query)
    parts = query.split(maxsplit=2)
    if len(parts) < 2:
        return "Datei-Skill: nutze `datei lies <pfad>`, `datei suche <text>`, `datei liste [ordner]`, `datei info <pfad>`, `datei schreibe <pfad> :: <text>` oder `datei sende <pfad>`."
    action = parts[1].lower()
    value = parts[2] if len(parts) > 2 else ""
    if action in {"lies", "read"}:
        path = Path(value)
        decision = context.permissions.check_path(path)
        if decision.needs_confirmation:
            context.logger.log("warn", "security", "Dateizugriff braucht Bestätigung", {"path": str(path), "reason": decision.reason})
            return f"Dafür brauche ich erst deine Freigabe: {decision.reason}"
        if not path.exists() or not path.is_file():
            return "Diese Datei finde ich nicht."
        text = path.read_text(encoding="utf-8", errors="replace")
        context.memory.save("files", f"read:{path}", f"Gelesene Datei: {path}", source=context.source, confidence=0.95)
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
                        context.memory.save("files", f"found:{path}", f"Gefundene Datei: {path}", source=context.source, confidence=0.82)
                if len(matches) >= 20:
                    break
        return "Treffer:\n" + "\n".join(matches) if matches else "Keine lokalen Treffer gefunden."
    if action in {"liste", "list"}:
        root = Path(value.strip()) if value.strip() else Path(context.settings.allowed_paths[0])
        decision = context.permissions.check_path(root)
        if decision.needs_confirmation:
            context.logger.log("warn", "security", "Datei-Listenzugriff braucht Bestätigung", {"path": str(root), "reason": decision.reason})
            return f"Dafür brauche ich erst deine Freigabe: {decision.reason}"
        if not root.exists() or not root.is_dir():
            return "Diesen Ordner finde ich nicht."
        entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:80]
        lines = [f"Dateien in {root}:"]
        for path in entries:
            kind = "Datei" if path.is_file() else "Ordner"
            detail = f" ({path.stat().st_size} Bytes)" if path.is_file() else ""
            lines.append(f"- {kind}: {path.name}{detail}")
            context.memory.save("files", f"listed:{path}", f"Bekannter Pfad: {path}", source=context.source, confidence=0.72)
        return "\n".join(lines)
    if action == "info":
        path = Path(value.strip())
        decision = context.permissions.check_path(path)
        if decision.needs_confirmation:
            context.logger.log("warn", "security", "Datei-Infozugriff braucht Bestätigung", {"path": str(path), "reason": decision.reason})
            return f"Dafür brauche ich erst deine Freigabe: {decision.reason}"
        if not path.exists():
            return "Diesen Pfad finde ich nicht."
        stat = path.stat()
        context.memory.save("files", f"info:{path}", f"Datei/Ordner-Info: {path}", source=context.source, confidence=0.9)
        return f"Pfad: {path}\nTyp: {'Datei' if path.is_file() else 'Ordner'}\nGröße: {stat.st_size} Bytes"
    if action in {"sende", "send", "schick"}:
        return _send_file_or_folder(value, context)
    if action in {"schreibe", "write"}:
        if "::" not in value:
            return "Nutze `datei schreibe <pfad> :: <text>`."
        raw_path, content = value.split("::", 1)
        path = Path(raw_path.strip())
        decision = context.permissions.check_path(path)
        if decision.needs_confirmation:
            context.logger.log("warn", "security", "Datei-Schreibzugriff braucht Bestätigung", {"path": str(path), "reason": decision.reason})
            return f"Dafür brauche ich erst deine Freigabe: {decision.reason}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip(), encoding="utf-8")
        context.logger.log("info", "file", "Datei geschrieben", {"path": str(path)})
        context.memory.save("files", f"written:{path}", f"Erstellte/geschriebene Datei: {path}", source=context.source, confidence=1.0)
        return f"Datei geschrieben: {path}"
    return "Diese Datei-Aktion kenne ich noch nicht."


def _normalize_query(query: str) -> str:
    stripped = query.strip()
    lowered = stripped.lower()
    if lowered.startswith(("erstelle datei ", "schreibe datei ")):
        rest = re.sub(r"^(erstelle|schreibe) datei\s+", "", stripped, flags=re.IGNORECASE)
        return f"datei schreibe {rest}"
    if lowered.startswith(("sende datei ", "schick datei ", "sende mir datei ", "schick mir datei ")):
        rest = re.sub(r"^(sende|schick)(\s+mir)?\s+datei\s+", "", stripped, flags=re.IGNORECASE)
        return f"datei sende {rest}"
    if lowered.startswith(("sende mir die datei ", "schick mir die datei ", "sende die datei ", "schick die datei ")):
        rest = re.sub(r"^(sende|schick)(\s+mir)?\s+die\s+datei\s+", "", stripped, flags=re.IGNORECASE)
        return f"datei sende {rest}"
    if lowered in {"sende letzte datei", "sende mir die letzte datei", "schick letzte datei", "schick mir die letzte datei"}:
        return "datei sende letzte"
    if lowered.startswith(("sende ordner ", "schick ordner ", "sende mir ordner ", "schick mir ordner ", "sende mir den ordner ", "schick mir den ordner ", "sende den ordner ", "schick den ordner ")):
        rest = re.sub(r"^(sende|schick)(\s+mir)?\s+(den\s+)?ordner\s+", "", stripped, flags=re.IGNORECASE)
        return f"datei sende {rest}"
    if lowered.startswith(("liste dateien", "dateien liste")):
        rest = re.sub(r"^(liste dateien|dateien liste)\s*", "", stripped, flags=re.IGNORECASE)
        return f"datei liste {rest}".strip()
    if lowered.startswith("lies datei "):
        rest = re.sub(r"^lies datei\s+", "", stripped, flags=re.IGNORECASE)
        return f"datei lies {rest}"
    if "suche lokal" in lowered or "lokal suche" in lowered:
        rest = re.sub(r"^(suche lokal|lokal suche)\s+", "", stripped, flags=re.IGNORECASE)
        rest = re.sub(r"^nach\s+", "", rest, flags=re.IGNORECASE)
        rest = re.sub(r"\s+im\s+workspace$", "", rest, flags=re.IGNORECASE)
        return f"datei suche {rest}".strip()
    return stripped


def _send_file_or_folder(value: str, context) -> str:
    target = value.strip().strip('"')
    if not target:
        return "Welche Datei soll ich dir schicken?"
    if target.lower() in {"letzte", "letzte datei", "die letzte datei"}:
        remembered = _last_remembered_file(context)
        if not remembered:
            return "Ich kenne noch keine letzte Datei, die ich schicken kann."
        target = str(remembered)

    path = Path(target)
    decision = context.permissions.check_path(path)
    if decision.needs_confirmation:
        context.logger.log("warn", "security", "Datei-Sendezugriff braucht Bestätigung", {"path": str(path), "reason": decision.reason})
        return f"Dafür brauche ich erst deine Freigabe: {decision.reason}"
    if not path.exists():
        return "Diese Datei oder diesen Ordner finde ich nicht."

    send_path = _zip_folder(path, context) if path.is_dir() else path
    if not send_path.exists() or not send_path.is_file():
        return "Diesen Pfad kann ich nicht als Datei verschicken."
    size = send_path.stat().st_size
    if size > MAX_DISCORD_ATTACHMENT_BYTES:
        mb = size / (1024 * 1024)
        limit = MAX_DISCORD_ATTACHMENT_BYTES // (1024 * 1024)
        return f"Die Datei ist mit {mb:.1f} MB zu groß für Discord. Limit: {limit} MB."

    context.memory.save("files", f"sent:{send_path}", f"Gesendete Datei: {send_path}", source=context.source, confidence=0.95)
    return f"Datei wird gesendet: {send_path}\n{ATTACH_MARKER}{send_path}"


def _zip_folder(path: Path, context) -> Path:
    outbox = Path(context.settings.workspace) / ".redclaw_outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.name or "ordner").strip("_") or "ordner"
    archive = outbox / f"{safe_name}-{int(time.time())}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for child in sorted(path.rglob("*")):
            if child.is_file():
                zip_handle.write(child, child.relative_to(path))
    context.memory.save("files", f"packed:{archive}", f"Ordner als ZIP gepackt: {path} -> {archive}", source=context.source, confidence=0.9)
    return archive


def _last_remembered_file(context) -> Path | None:
    for item in context.memory.list_by_category("files", limit=40):
        key = getattr(item, "key", "")
        if key.startswith(("written:", "found:", "read:", "info:")):
            path = Path(key.split(":", 1)[1])
            if path.exists() and path.is_file():
                return path
    return None
