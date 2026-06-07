# RedClaw

RedClaw ist ein lokaler, ueberwachbarer Agent fuer Redcrafter. Er laeuft auf
einem Raspberry Pi 5 mit Raspberry Pi OS 64-bit, spricht nur per Discord-DM mit
der konfigurierten User-ID und bietet ein dunkles lokales Web-Dashboard.

## Funktionen

- Discord-DM-Bot, nur fuer eine konfigurierte Discord-User-ID
- Lokales Web-Interface mit Login, Chat, Live-Logs, Memory, Skills und Config
- SQLite-Memory mit Kategorien und Vergessen-Funktion
- Reminder ueber APScheduler
- Plugin-/Skill-System
- Skill-Builder, der Codex CLI neue Skills schreiben und Tests ausfuehren laesst
- Ueberwachte Shell-Jobs mit Risk-Leveln
- Codex CLI per `codex exec --json`
- Brave Search API fuer Websuche
- NVIDIA NIM API-Key-Support ueber OpenAI-kompatible Chat-Endpunkte
- Edge-TTS fuer Web-Voice-Ausgabe
- Docker Compose fuer Raspberry Pi arm64

## Schnellstart lokal

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
python scripts/create_workspace.py
python scripts/run_systemcheck.py
uvicorn redclaw.web.app:app --host 0.0.0.0 --port 8080
```

Auf Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/init_db.py
python scripts/create_workspace.py
python scripts/run_systemcheck.py
uvicorn redclaw.web.app:app --host 0.0.0.0 --port 8080
```

Web-UI: `http://localhost:8080`

Standard-Login:

- Benutzer: `redcrafter`
- Passwort: `redclaw`

Setze danach ein eigenes Passwort in `.env` oder `config/redclaw.yaml`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## Konfiguration

Wichtige Werte in `.env`:

```env
DISCORD_TOKEN=
REDSCRAFTER_DISCORD_ID=
BRAVE_SEARCH_API_KEY=
NVIDIA_NIM_API_KEY=
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5
CODEX_COMMAND=codex
```

Die gleiche Konfiguration kann im Web-Dashboard unter `Config` gespeichert
werden. RedClaw schreibt dann `config/redclaw.yaml`.

## NVIDIA NIM

RedClaw nutzt NVIDIA NIM ueber den OpenAI-kompatiblen Chat-Endpunkt. Der
Default ist:

```text
https://integrate.api.nvidia.com/v1/chat/completions
```

Du brauchst:

- `NVIDIA_NIM_API_KEY`
- `NVIDIA_NIM_BASE_URL`
- `NVIDIA_NIM_MODEL`

Der NIM-Skill wird mit Nachrichten erkannt, die `NVIDIA` oder `NIM` enthalten.

## Sicherheit

RedClaw darf Shell und Codex benutzen, arbeitet aber mit Risk-Leveln:

- `safe`: wird ausgefuehrt
- `needs_confirmation`: wird angehalten und im Security-Log markiert
- `blocked`: wird blockiert

Gefaehrlich sind Paketinstallationen, Loeschbefehle, systemkritische Befehle,
Docker-Neustarts, Reboots und Downloads von unbekannten Quellen.

Dateizugriff ist nur in freigegebenen Ordnern erlaubt. Der Standard-Workspace
ist `/home/pi/redclaw_workspace`.

## Tests

```bash
pytest -q
```

## Codex CLI

Installiere und authentifiziere Codex CLI auf dem Pi. RedClaw startet Aufgaben
als ueberwachte Jobs:

```bash
codex exec --json --sandbox workspace-write "Aufgabe"
```

Lange Codex-Ausgaben erscheinen im Web-Dashboard unter Live/Logs.
