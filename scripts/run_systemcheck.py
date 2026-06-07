from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from redclaw.agent.systemcheck import run_systemcheck
from redclaw.config import get_settings


def main() -> None:
    for check in run_systemcheck(get_settings()):
        print(f"[{check.status}] {check.name}: {check.detail}")


if __name__ == "__main__":
    main()
