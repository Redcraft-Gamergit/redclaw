from __future__ import annotations

from pathlib import Path

from redclaw.discord.bot import _extract_attachments
from redclaw.skills.skill_files import ATTACH_MARKER


def test_extract_attachments_hides_markers():
    visible, paths = _extract_attachments(f"Datei wird gesendet\n{ATTACH_MARKER}/tmp/redclaw.txt")

    assert visible == "Datei wird gesendet"
    assert paths == [Path("/tmp/redclaw.txt")]
