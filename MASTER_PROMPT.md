# Master-Prompt fuer RedClaw

Baue ein vollstaendiges, modular aufgebautes Python-Projekt namens `RedClaw`.
RedClaw ist ein persoenlicher Agent fuer Redcrafter auf einem Raspberry Pi 5 mit
16 GB RAM und Raspberry Pi OS 64-bit. Das System soll sofort lokal lauffaehig,
Docker-faehig, ueberwachbar und sicher konfigurierbar sein.

## Hauptziel

RedClaw soll nur mit Redcrafter kommunizieren, ueber Discord-DMs und ueber ein
lokales Web-Interface. RedClaw hat Memory, Reminder, Skills, Websuche, lokale
Dateisuche, Shell-Zugriff, Codex-CLI-Integration, Web-Voice und ein Dashboard
fuer Logs, Memory, Skills, Config und Chat.

Das Projekt muss vollstaendigen Code liefern. Keine TODOs, keine Dummy-Module,
keine leeren Platzhalter. Beispiel-Config, Beispiel-Memory, Beispiel-Skills,
Docker-Compose, Startbefehle und Tests muessen enthalten sein.

## Zielplattform

- Raspberry Pi 5
- 16 GB RAM
- Raspberry Pi OS 64-bit
- Docker und Docker Compose
- Python 3.11 oder neuer
- SQLite als Datenbank
- Codex CLI auf dem Host oder im passenden Container, bevorzugt per Job/Queue

## Ordnerstruktur

Erstelle diese Struktur:

```text
redclaw/
  agent/
    __init__.py
    core.py
    intents.py
    router.py
    permissions.py
    jobs.py
    logging_service.py
    systemcheck.py
  discord/
    __init__.py
    bot.py
  web/
    __init__.py
    app.py
    auth.py
    websocket.py
    voice.py
    templates/
    static/
  skills/
    __init__.py
    base.py
    skill_time.py
    skill_system.py
    skill_search.py
    skill_files.py
    skill_shell.py
    skill_codex.py
    skill_memory.py
  memory/
    __init__.py
    db.py
    models.py
    repository.py
    extractor.py
  reminders/
    __init__.py
    scheduler.py
  config/
    config.example.yaml
  logs/
    .gitkeep
  tests/
    test_memory.py
    test_permissions.py
    test_skills.py
    test_intents.py
  scripts/
    init_db.py
    create_workspace.py
    run_systemcheck.py
  docker/
    Dockerfile.agent
    Dockerfile.discord
    Dockerfile.web
  docker-compose.yml
  requirements.txt
  README.md
  .env.example
```

## Kommunikation

### Discord

- Nutze `discord.py`.
- RedClaw reagiert nur auf Direktnachrichten.
- RedClaw reagiert nur auf die konfigurierte Discord-User-ID.
- Die Discord-User-ID wird ueber die Web-Config und Config-Datei gesetzt.
- Nachrichten anderer User oder aus Server-Channels werden ignoriert und als
  Security-Event geloggt.
- Reminder duerfen Discord-DMs an Redcrafter senden.

### Web-Interface

Baue das Web-Interface mit FastAPI, Jinja2, HTMX und WebSockets. Verwende ein
dunkles, schlichtes Dashboard-Design. Kein React verwenden.

Das Web-Interface ist nur lokal gedacht und soll nicht als oeffentliches
Internet-Frontend konzipiert werden.

Funktionen:

- Login mit Benutzername und Passwort
- Nur ein Benutzer: Redcrafter
- Passwort-Hashing mit `passlib` oder `bcrypt`
- Dashboard
- Chat-Konsole
- Live-Logs ueber WebSocket
- Live-Shell-Ausgaben ueber WebSocket
- Memory-Viewer mit Suche, Kategorien und Loeschfunktion fuer einzelne Fakten
- Skill-Manager
- Skill aktivieren/deaktivieren
- Skill-Ausfuehrung testen
- Config-Seite fuer Discord-ID, erlaubte Ordner, API-Keys und RedClaw-Stil
- API-Key-Verwaltung fuer Brave Search und optionale Dienste
- Panik-Knopf zum Stoppen laufender Jobs
- Systemcheck-Seite
- Voice-Eingabe und Voice-Ausgabe

### Voice

- Web-Voice soll Sprache erkennen und RedClaw soll per Stimme antworten.
- Fuer TTS bevorzugt `edge-tts` oder eine vergleichbare leichte Loesung.
- Sprache ist standardmaessig Deutsch.
- Sprache und Stil sollen konfigurierbar und im Memory speicherbar sein.

## Agent-Core

Der Agent-Core verarbeitet alle Nachrichten von Discord und Web.

Aufgaben:

- Intent-Erkennung mit Regeln und einfacher KI-Logik
- Skill-Routing
- Memory-Extraktion
- Memory-Suche
- Reminder-Erkennung
- Shell- und Dateiberechtigungen pruefen
- Codex-CLI-Jobs starten
- Logs schreiben
- Antworten auf Deutsch generieren

Der Agent soll standardmaessig Deutsch antworten. Ton und Ansprache sollen in
der Config und im Memory einstellbar sein.

## Memory

Nutze SQLite, nicht JSON.

Memory soll aus Gespraechen relevante Informationen extrahieren und in
Kategorien speichern. Nicht einfach nur kompletten Chatverlauf blind als Memory
verwenden.

Kategorien:

- Fakten ueber Redcrafter
- Praeferenzen
- Aufgaben
- Projekte
- Personen
- technische Umgebung
- laufende Ziele
- Erinnerungen
- geloeschte/vergessene Fakten

API:

```python
memory.save(category, key, value, source=None, confidence=1.0)
memory.get(category, key)
memory.search(query, category=None)
memory.delete(memory_id)
memory.list_by_category(category)
```

RedClaw muss beantworten koennen:

- "Was weisst du ueber mich?"
- "Vergiss, dass ich X mag."
- "Welche Aufgaben habe ich offen?"

## Reminder

Nutze APScheduler.

RedClaw soll Erinnerungen erkennen, speichern und ausfuehren:

- "Erinnere mich in 10 Minuten an Tee."
- "Erinnere mich morgen um 18 Uhr an Einkauf."
- "Zeig mir meine Erinnerungen."
- "Loesche Erinnerung X."

Reminder werden in SQLite gespeichert und beim Start wieder geladen.

## Skills

Skills liegen in `/skills` und sind Python-Module. Jeder Skill hat ein Manifest
und eine `run(query, context)` Funktion.

Skill-Format:

```python
SKILL = {
    "name": "time",
    "description": "Gibt Datum und Uhrzeit aus.",
    "permissions": [],
    "enabled": True,
}

def run(query, context):
    return "Antwort"
```

Beispiel-Skills:

- `skill_time.py`: Uhrzeit und Datum
- `skill_system.py`: CPU, RAM, Temperatur, Disk, Docker-Status
- `skill_search.py`: Websuche
- `skill_files.py`: Dateien lesen, schreiben, suchen in erlaubten Ordnern
- `skill_shell.py`: Shell-Befehle mit Permissions und Live-Output
- `skill_codex.py`: Codex CLI per Job/Queue
- `skill_memory.py`: Memory lesen, suchen, vergessen

Neue Skills:

- RedClaw darf neue Skills selbst erstellen.
- Codex CLI darf Skill-Code direkt in `/skills` schreiben.
- Nach jeder Skill-Erstellung oder Aenderung muessen automatische Tests laufen.
- Neue Skills duerfen aktiviert werden.
- Jede Skill-Aenderung wird per Git versioniert.

## Websuche

Nutze Brave Search API als Standard-Websuche.

Anforderungen:

- API-Key ueber Config oder Web-UI
- Suchergebnisse zusammenfassen
- Quellen-URLs anzeigen
- Webinhalte als untrusted behandeln
- Keine Downloads von unbekannten/komischen Websites ohne Bestaetigung

Optional vorbereiten:

- Tavily oder Exa als spaeter aktivierbarer Spezial-Skill fuer KI-Recherche

## Codex CLI

RedClaw soll Codex CLI nutzen koennen.

Bevorzugte Nutzung:

- `codex exec --json`
- Jobs laufen in einer Queue
- Ausgabe wird live ins Web-UI gestreamt
- Finales Ergebnis wird in Logs und optional Memory gespeichert
- Codex darf Skills schreiben, Tests ausfuehren und Git nutzen

Codex-Jobs sollen nicht die Discord-Antwort blockieren. Wenn ein Job laenger
dauert, antwortet RedClaw kurz, dass der Job gestartet wurde, und meldet das
Ergebnis spaeter.

## Rechte und Sicherheit

RedClaw hat grundsaetzlich starke Rechte, aber alles muss ueberwacht werden.

Regeln:

- Shell-Befehle sind erlaubt.
- Dateizugriff nur in erlaubten Ordnern.
- Start-Workspace `/home/pi/redclaw_workspace` automatisch erstellen.
- Neue erlaubte Ordner muessen einmalig bestaetigt werden.
- Systembefehle duerfen nach Bestaetigung ausgefuehrt werden.
- Docker-Container duerfen nach Bestaetigung neu gebaut und gestartet werden.
- Git darf benutzt werden.
- Gefaehrliche Aktionen brauchen Rueckfrage.
- Panik-Knopf stoppt laufende Jobs.

Gefaehrliche Aktionen:

- Paketinstallation, z. B. `apt install`, `pip install`, `npm install`
- Loeschen von Dateien oder Ordnern
- rekursives Loeschen
- systemkritische Befehle
- Reboot oder Shutdown
- Docker-Neubau oder Container-Neustart
- Downloads von unbekannten oder komischen Websites
- Aenderungen ausserhalb erlaubter Ordner

Implementiere `permissions.py` mit klaren Checks und Risk-Leveln:

- `safe`
- `needs_confirmation`
- `blocked`

## Logging

Logs werden 50 Tage gespeichert. Danach duerfen technische Logs automatisch
bereinigt werden. Security-relevante Logs sollen laenger erhalten bleiben oder
separat markiert werden.

Log-Typen:

- Chat-Log
- Skill-Log
- Shell-Log
- File-Log
- Codex-Log
- Security-Log
- System-Log
- Web-Login-Log

Alle Logs sollen im Web-UI sichtbar sein. Laufende Shell- und Codex-Ausgaben
sollen live per WebSocket sichtbar sein.

## Systemcheck

Beim Start laeuft automatisch ein Systemcheck:

- Python-Version
- SQLite erreichbar
- Workspace vorhanden
- erlaubte Ordner vorhanden
- Discord-Config gesetzt
- Brave-API-Key gesetzt oder Warnung
- Codex CLI installiert oder Warnung
- Docker erreichbar
- CPU/RAM/Disk/Temperatur
- Schreibrechte in `/home/pi/redclaw_workspace`

Systemcheck-Ergebnisse werden im Web-UI angezeigt und geloggt.

## Docker

Erstelle Docker Compose fuer:

- `agent`
- `discordbot`
- `web`
- optional `worker`, falls sinnvoll

Gemeinsame Volumes:

- SQLite-Datenbank
- Logs
- Skills
- Config
- `/home/pi/redclaw_workspace`

Docker muss fuer Raspberry Pi arm64 geeignet sein.

## Tests

Erstelle Tests fuer:

- Memory speichern/suchen/loeschen
- Permission-Risk-Level
- gefaehrliche Shell-Befehle
- erlaubte und nicht erlaubte Dateipfade
- Skill-Loader
- Beispiel-Skills
- Intent-Erkennung fuer Reminder

README muss zeigen:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
python scripts/create_workspace.py
python scripts/run_systemcheck.py
uvicorn web.app:app --host 0.0.0.0 --port 8080
```

Und fuer Docker:

```bash
docker compose up --build
```

## Qualitaetsregeln

- Kein toter Code.
- Keine TODOs.
- Keine leeren Platzhalter.
- Keine geheimen Keys im Repo.
- Config-Beispiele mit Dummy-Werten.
- Saubere Fehlerbehandlung.
- Klare Logs.
- Alle Module importierbar.
- Tests muessen laufen.
- Pi-schonend: keine schweren Frontend-Bundles, keine unnoetigen Hintergrundprozesse.
- UI dunkel, schlicht, funktional.
- RedClaw ist nur fuer Redcrafter.

## Erwartetes Ergebnis

Liefere ein komplettes Projekt mit Code, Tests, README, Docker Compose,
Beispiel-Config, Beispiel-Skills und Startanleitung. Nach dem Start soll
RedClaw lokal nutzbar sein, Web-Login anbieten, einen Systemcheck anzeigen,
Discord-DMs verarbeiten, Memory nutzen, Skills ausfuehren, Reminder setzen,
Websuche nutzen und Codex CLI als Job ausfuehren koennen.
