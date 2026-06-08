from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass

import discord


@dataclass
class TestResult:
    prompt: str
    answer: str


class RedClawTestClient(discord.Client):
    def __init__(self, target_user_id: int, prompts: list[str], timeout_seconds: int = 45):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.target_user_id = target_user_id
        self.prompts = prompts
        self.timeout_seconds = timeout_seconds
        self.results: list[TestResult] = []
        self._current_prompt: str | None = None
        self._response_event = asyncio.Event()
        self._dm_channel: discord.DMChannel | None = None

    async def on_ready(self) -> None:
        target = await self.fetch_user(self.target_user_id)
        self._dm_channel = await target.create_dm()
        for prompt in self.prompts:
            self._current_prompt = prompt
            self._response_event.clear()
            await self._dm_channel.send(prompt)
            try:
                await asyncio.wait_for(self._response_event.wait(), timeout=self.timeout_seconds)
            except asyncio.TimeoutError:
                self.results.append(TestResult(prompt, "<timeout>"))
        await self.close()

    async def on_message(self, message: discord.Message) -> None:
        if message.author.id != self.target_user_id or not self._current_prompt:
            return
        self.results.append(TestResult(self._current_prompt, message.content))
        self._response_event.set()


async def main() -> int:
    token = os.getenv("REDCLAW_TEST_DISCORD_TOKEN")
    target_raw = os.getenv("REDCLAW_TARGET_DISCORD_BOT_ID")
    if not token or not target_raw:
        print("REDCLAW_TEST_DISCORD_TOKEN und REDCLAW_TARGET_DISCORD_BOT_ID müssen gesetzt sein.", file=sys.stderr)
        return 2
    prompts = [
        "Hey",
        "was ist 1 + 1",
        "datei schreibe /home/redcraft/redclaw_workspace/discord-test.txt :: Discord Test",
        "wo liegt die discord-test datei?",
    ]
    client = RedClawTestClient(int(target_raw), prompts)
    await client.start(token)
    for result in client.results:
        print(f"PROMPT: {result.prompt}")
        print(f"ANSWER: {result.answer[:500]}")
        print("---")
    return 1 if any(result.answer == "<timeout>" for result in client.results) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
