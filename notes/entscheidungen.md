# RedClaw Entscheidungen

## Identitaet
- Name: RedClaw
- Sprache: Deutsch als Standard, später einstellbar
- Ton/Ansprache: einstellbar und im Memory speicherbar

## Discord
- Nur Direktnachrichten
- Nur Redcrafter/User-ID aus Config
- Discord-User-ID wird über die Web-Config einstellbar

## Web
- Web-Interface ja
- Nicht aus dem Internet offen erreichbar
- Login per Passwort
- Web-Login nur für einen Benutzer: Redcrafter
- Web-Sprachbefehle geplant
- Web-Voice soll Sprache erkennen und RedClaw soll auch per Stimme antworten
- Text-to-Speech bevorzugt über Edge-TTS oder vergleichbar
- Live-Ansicht für Aktionen/Logs
- Shell-Ausgaben sollen live im Web-UI sichtbar sein
- Panik-Knopf soll alle laufenden Jobs stoppen
- Dark UI

## Rechte und Sicherheit
- Shell-Befehle erlaubt
- Alles wird überwacht/protokolliert
- Gefährliche Aktionen brauchen Rueckfrage
- Dateirechte nur in bestimmten erlaubten Ordnern
- Neue Ordner müssen einmalig erlaubt werden
- Start-Ordner für erlaubten Dateizugriff: ja, z. B. /home/pi/redclaw_workspace
- Systembefehle wie apt install, systemctl, Docker-Neustarts und Reboot sind nach Bestätigung erlaubt
- Gefährlich sind besonders: Paketinstallation, Löschen, systemzerstörende Aktionen und Downloads von unbekannten/komischen Websites
- Docker-Container dürfen nach Bestätigung neu gebaut und gestartet werden
- Git darf benutzt werden, z. B. für Skill-Versionierung und Rollback

## Memory
- SQLite empfohlen
- Lernt aus allen Gesprächen, extrahiert aber relevante Infos und speichert sie in Kategorien
- Vergessen-Funktion noetig
- Einzelne Fakten müssen gelöscht werden können
- RedClaw soll beantworten können, was er über den User weiß

## Suche und Medien
- Lokale Dateisuche ist erlaubt
- Websuche über API
- Bilder und Screenshots sollen später verstanden werden

## Skills
- Skills können über Web-UI verwaltet werden
- RedClaw soll Skills selbst erstellen können
- Codex CLI kann Skill-Code erzeugen
- Neue Skills dürfen direkt in /skills geschrieben werden
- Nach neuen oder geänderten Skills müssen automatisch Tests laufen
- Neue Skills dürfen aktiviert werden

## System
- Zielgeraet: Raspberry Pi 5, 16 GB RAM
- OS: Raspberry Pi OS 64-bit
- Docker: ja
- Codex CLI: ja, bevorzugt per Job/Queue
- Backups: keine externen Backups gewuenscht
- Nur ein Benutzer: Redcrafter
- Log-Aufbewahrung: 50 Tage
- /home/pi/redclaw_workspace soll automatisch erstellt werden
- Beim Start soll automatisch ein Systemcheck laufen
