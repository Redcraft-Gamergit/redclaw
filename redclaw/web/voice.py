from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import edge_tts


async def synthesize(text: str, output_dir: Path, voice: str = "de-DE-ConradNeural") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"redclaw-{uuid4().hex}.mp3"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(path))
    return path
