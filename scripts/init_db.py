from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from redclaw.config import get_settings
from redclaw.memory.db import init_db


def main() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    init_db(settings.db_path)
    print(f"SQLite initialisiert: {settings.db_path}")


if __name__ == "__main__":
    main()
