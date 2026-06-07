from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from redclaw.config import get_settings


def main() -> None:
    settings = get_settings()
    settings.workspace.mkdir(parents=True, exist_ok=True)
    print(f"Workspace bereit: {settings.workspace}")


if __name__ == "__main__":
    main()
