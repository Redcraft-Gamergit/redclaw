# RedClaw Entscheidungen

## Identitaet
- Name: RedClaw
- Sprache: Deutsch als Standard, spaeter einstellbar
- Ton/Ansprache: einstellbar und im Memory speicherbar

## Discord
- Nur Direktnachrichten
- Nur Redcrafter/User-ID aus Config
- Discord-User-ID wird ueber die Web-Config einstellbar

## Web
- Web-Interface ja
- Nicht aus dem Internet offen erreichbar
- Login per Passwort
- Web-Login nur fuer einen Benutzer: Redcrafter
- Web-Sprachbefehle geplant
- Web-Voice soll Sprache erkennen und RedClaw soll auch per Stimme antworten
- Text-to-Speech bevorzugt ueber Edge-TTS oder vergleichbar
- Live-Ansicht fuer Aktionen/Logs
- Shell-Ausgaben sollen live im Web-UI sichtbar sein
- Panik-Knopf soll alle laufenden Jobs stoppen
- Dark UI

## Rechte und Sicherheit
- Shell-Befehle erlaubt
- Alles wird ueberwacht/protokolliert
- Gefaehrliche Aktionen brauchen Rueckfrage
- Dateirechte nur in bestimmten erlaubten Ordnern
- Neue Ordner muessen einmalig erlaubt werden
- Start-Ordner fuer erlaubten Dateizugriff: ja, z. B. /home/pi/redclaw_workspace
- Systembefehle wie apt install, systemctl, Docker-Neustarts und Reboot sind nach Bestaetigung erlaubt
- Gefaehrlich sind besonders: Paketinstallation, Loeschen, systemzerstoerende Aktionen und Downloads von unbekannten/komischen Websites
- Docker-Container duerfen nach Bestaetigung neu gebaut und gestartet werden
- Git darf benutzt werden, z. B. fuer Skill-Versionierung und Rollback

## Memory
- SQLite empfohlen
- Lernt aus allen Gespraechen, extrahiert aber relevante Infos und speichert sie in Kategorien
- Vergessen-Funktion noetig
- Einzelne Fakten muessen geloescht werden koennen
- RedClaw soll beantworten koennen, was er ueber den User weiss

## Suche und Medien
- Lokale Dateisuche ist erlaubt
- Websuche ueber API
- Bilder und Screenshots sollen spaeter verstanden werden

## Skills
- Skills koennen ueber Web-UI verwaltet werden
- RedClaw soll Skills selbst erstellen koennen
- Codex CLI kann Skill-Code erzeugen
- Neue Skills duerfen direkt in /skills geschrieben werden
- Nach neuen oder geaenderten Skills muessen automatisch Tests laufen
- Neue Skills duerfen aktiviert werden

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
