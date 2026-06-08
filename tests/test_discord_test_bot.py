from __future__ import annotations

from scripts.discord_test_bot import default_prompts, parse_prompts


def test_parse_prompts_uses_separator():
    assert parse_prompts("hey|||was ist 1 + 1|||  datei liste  ") == [
        "hey",
        "was ist 1 + 1",
        "datei liste",
    ]


def test_default_prompts_cover_long_chat_capabilities():
    prompts = "\n".join(default_prompts()).lower()
    assert "1 + 1" in prompts
    assert "erstelle datei" in prompts
    assert "sende datei" in prompts
    assert "erinnere mich" in prompts
    assert "mit wem chattest" in prompts
