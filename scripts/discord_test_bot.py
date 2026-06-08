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
    def __init__(
        self,
        target_user_id: int,
        prompts: list[str],
        timeout_seconds: int = 45,
        send_only: bool = False,
        channel_id: int | None = None,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.target_user_id = target_user_id
        self.prompts = prompts
        self.timeout_seconds = timeout_seconds
        self.send_only = send_only
        self.channel_id = channel_id
        self.results: list[TestResult] = []
        self._current_prompt: str | None = None
        self._response_event = asyncio.Event()
        self._dm_channel: discord.DMChannel | None = None

    async def on_ready(self) -> None:
        print(f"TESTBOT_READY:{self.user}", flush=True)
        if self.channel_id:
            channel = await self.fetch_channel(self.channel_id)
            self._dm_channel = channel
            print(f"CHANNEL:{channel}", flush=True)
        else:
            target = await self.fetch_user(self.target_user_id)
            print(f"TARGET:{target} bot={target.bot}", flush=True)
            self._dm_channel = await target.create_dm()
            print("DM_CREATED", flush=True)
        for prompt in self.prompts:
            self._current_prompt = prompt
            self._response_event.clear()
            print(f"SEND:{prompt}", flush=True)
            await self._dm_channel.send(prompt)
            if self.send_only:
                self.results.append(TestResult(prompt, "<sent>"))
                continue
            try:
                await asyncio.wait_for(self._response_event.wait(), timeout=self.timeout_seconds)
            except asyncio.TimeoutError:
                print(f"TIMEOUT:{prompt}", flush=True)
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
    channel_raw = os.getenv("REDCLAW_TEST_CHANNEL_ID")
    if not token or not target_raw:
        print("REDCLAW_TEST_DISCORD_TOKEN und REDCLAW_TARGET_DISCORD_BOT_ID müssen gesetzt sein.", file=sys.stderr)
        return 2
    prompts = [item.strip() for item in os.getenv("REDCLAW_TEST_PROMPTS", "").split("|||") if item.strip()]
    if not prompts:
        prompts = [
            "Hey",
            "was ist 1 + 1",
            "datei schreibe /home/redcraft/redclaw_workspace/discord-test.txt :: Discord Test",
            "datei sende /home/redcraft/redclaw_workspace/discord-test.txt",
            "wo liegt die discord-test datei?",
        ]
    send_only = os.getenv("REDCLAW_TEST_SEND_ONLY", "").lower() in {"1", "true", "yes", "on"}
    channel_id = int(channel_raw) if channel_raw else None
    client = RedClawTestClient(int(target_raw), prompts, send_only=send_only, channel_id=channel_id)
    try:
        await asyncio.wait_for(client.start(token), timeout=(len(prompts) * 60) + 30)
    except asyncio.TimeoutError:
        print("GLOBAL_TIMEOUT", file=sys.stderr, flush=True)
        await client.close()
        return 1
    except Exception as exc:
        print(f"TESTBOT_ERROR:{type(exc).__name__}:{exc}", file=sys.stderr, flush=True)
        await client.close()
        return 1
    for result in client.results:
        print(f"PROMPT: {result.prompt}")
        print(f"ANSWER: {result.answer[:500]}")
        print("---")
    return 1 if any(result.answer == "<timeout>" for result in client.results) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
