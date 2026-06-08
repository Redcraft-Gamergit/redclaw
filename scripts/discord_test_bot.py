from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import discord


PROMPT_SEPARATOR = "|||"


@dataclass
class TestResult:
    prompt: str
    answer: str


def _is_enabled(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on", "ja"}


def parse_prompts(raw: str | None) -> list[str]:
    return [item.strip() for item in str(raw or "").split(PROMPT_SEPARATOR) if item.strip()]


def default_prompts() -> list[str]:
    return [
        "Hey RedClaw, ich bin der Testbot. Antworte bitte normal wie in einem echten Chat.",
        "Was ist 1 + 1?",
        "Merke dir bitte: Der Testbot prueft heute Dateien, Memory, Skills und Chat-Kontext.",
        "Woran sollst du dich aus der letzten Nachricht erinnern?",
        "Erstelle datei /home/redcraft/redclaw_workspace/testbot/langchat.txt :: RedClaw Langchat Test. Der Bot soll sich merken, wo diese Datei liegt.",
        "Liste dateien /home/redcraft/redclaw_workspace/testbot",
        "Datei info /home/redcraft/redclaw_workspace/testbot/langchat.txt",
        "Sende datei /home/redcraft/redclaw_workspace/testbot/langchat.txt",
        "Wo liegt die Datei, die du gerade erstellt hast?",
        "Wie spaet ist es?",
        "Wie geht es deinem System gerade? Pruefe CPU RAM oder Temperatur, wenn du kannst.",
        "Mit wem chattest du gerade und welche Chatquellen kennst du?",
        "Erinnere mich in 2 Minuten an Testbot Langchat fertig machen.",
        "Suche lokal nach langchat im Workspace.",
        "Schreibe datei /home/redcraft/redclaw_workspace/testbot/zweite-notiz.txt :: Zweite Notiz aus dem langen Testchat.",
        "Welche Dateien hast du in diesem Test erstellt?",
        "Erklaere kurz, was du alles kannst: chatten, erinnern, Dateien, Skills, Suche und Codex.",
        "Fasse unser Testgespraech zusammen und sage, was du dir merken solltest.",
    ]


def get_prompts() -> list[str]:
    return parse_prompts(os.getenv("REDCLAW_TEST_PROMPTS")) or default_prompts()


def transcript_path() -> Path | None:
    raw = os.getenv("REDCLAW_TEST_TRANSCRIPT", "").strip()
    if not raw:
        return None
    return Path(raw)


def write_transcript(results: list[TestResult]) -> None:
    path = transcript_path()
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for index, result in enumerate(results, 1):
            handle.write(f"## Runde {index}\n")
            handle.write(f"USER: {result.prompt}\n")
            handle.write(f"REDCLAW: {result.answer}\n\n")


def print_results(results: list[TestResult], max_chars: int = 1200) -> None:
    for result in results:
        print(f"PROMPT: {result.prompt}")
        answer = result.answer
        if len(answer) > max_chars:
            answer = f"{answer[:max_chars]}..."
        print(f"ANSWER: {answer}")
        print("---")


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
        self._message_channel: discord.abc.Messageable | None = None

    async def on_ready(self) -> None:
        print(f"TESTBOT_READY:{self.user}", flush=True)
        if self.channel_id:
            channel = await self.fetch_channel(self.channel_id)
            self._message_channel = channel
            print(f"CHANNEL:{channel}", flush=True)
        else:
            target = await self.fetch_user(self.target_user_id)
            print(f"TARGET:{target} bot={target.bot}", flush=True)
            self._message_channel = await target.create_dm()
            print("DM_CREATED", flush=True)

        for prompt in self.prompts:
            self._current_prompt = prompt
            self._response_event.clear()
            print(f"SEND:{prompt}", flush=True)
            await self._message_channel.send(prompt)
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
        content = message.content or ""
        if message.attachments:
            attachment_names = ", ".join(attachment.filename for attachment in message.attachments)
            content = f"{content}\n[attachments: {attachment_names}]".strip()
        self.results.append(TestResult(self._current_prompt, content))
        self._response_event.set()


async def run_discord(prompts: list[str]) -> int:
    token = os.getenv("REDCLAW_TEST_DISCORD_TOKEN")
    target_raw = os.getenv("REDCLAW_TARGET_DISCORD_BOT_ID")
    channel_raw = os.getenv("REDCLAW_TEST_CHANNEL_ID")
    if not token or not target_raw:
        print("REDCLAW_TEST_DISCORD_TOKEN and REDCLAW_TARGET_DISCORD_BOT_ID must be set.", file=sys.stderr)
        return 2

    send_only = _is_enabled(os.getenv("REDCLAW_TEST_SEND_ONLY"))
    timeout_seconds = int(os.getenv("REDCLAW_TEST_TIMEOUT", "45"))
    channel_id = int(channel_raw) if channel_raw else None
    client = RedClawTestClient(
        int(target_raw),
        prompts,
        timeout_seconds=timeout_seconds,
        send_only=send_only,
        channel_id=channel_id,
    )
    try:
        await asyncio.wait_for(client.start(token), timeout=(len(prompts) * (timeout_seconds + 15)) + 30)
    except asyncio.TimeoutError:
        print("GLOBAL_TIMEOUT", file=sys.stderr, flush=True)
        await client.close()
        return 1
    except Exception as exc:
        print(f"TESTBOT_ERROR:{type(exc).__name__}:{exc}", file=sys.stderr, flush=True)
        await client.close()
        return 1
    write_transcript(client.results)
    print_results(client.results)
    return 1 if any(result.answer == "<timeout>" for result in client.results) else 0


async def run_direct(prompts: list[str]) -> int:
    from redclaw.bootstrap import Runtime
    from redclaw.config import get_settings

    runtime = Runtime(get_settings())
    results: list[TestResult] = []
    for index, prompt in enumerate(prompts, 1):
        print(f"DIRECT_SEND:{index}:{prompt}", flush=True)
        try:
            answer = await runtime.agent.handle_message(prompt, source="discord_testbot")
        except Exception as exc:
            answer = f"<error:{type(exc).__name__}:{exc}>"
        print(f"DIRECT_ANSWER:{index}:{answer[:500]}", flush=True)
        results.append(TestResult(prompt, answer))
    write_transcript(results)
    print_results(results)
    return 1 if any(result.answer.startswith("<error:") for result in results) else 0


async def run_interactive() -> int:
    from redclaw.bootstrap import Runtime
    from redclaw.config import get_settings

    runtime = Runtime(get_settings())
    results: list[TestResult] = []
    print("INTERACTIVE_READY. Type a message and press Enter. Type /quit to stop.", flush=True)
    while True:
        prompt = await asyncio.to_thread(sys.stdin.readline)
        if not prompt:
            break
        prompt = prompt.strip()
        if not prompt:
            continue
        if prompt.lower() in {"/quit", "/exit"}:
            break
        answer = await runtime.agent.handle_message(prompt, source="discord_testbot")
        print(answer, flush=True)
        results.append(TestResult(prompt, answer))
    write_transcript(results)
    return 0


async def main() -> int:
    mode = os.getenv("REDCLAW_TEST_MODE", "auto").strip().lower()
    prompts = get_prompts()

    if _is_enabled(os.getenv("REDCLAW_TEST_INTERACTIVE")) or mode == "interactive":
        return await run_interactive()
    if mode == "direct":
        return await run_direct(prompts)
    if mode == "discord":
        return await run_discord(prompts)

    if os.getenv("REDCLAW_TEST_CHANNEL_ID"):
        print("AUTO_MODE: using Discord test channel.", flush=True)
        return await run_discord(prompts)

    print("AUTO_MODE: no REDCLAW_TEST_CHANNEL_ID set; using direct RedClaw core chat.", flush=True)
    print("AUTO_MODE: Discord bot-to-bot DMs are blocked by Discord unless both bots share a channel.", flush=True)
    return await run_direct(prompts)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
