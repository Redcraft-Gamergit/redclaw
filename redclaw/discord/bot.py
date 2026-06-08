from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from pathlib import Path

import discord

from redclaw.bootstrap import get_runtime
from redclaw.skills.skill_files import ATTACH_MARKER, MAX_DISCORD_ATTACHMENT_BYTES


runtime = get_runtime()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("redclaw.discord")


class RedClawClient(discord.Client):
    async def on_ready(self) -> None:
        log.info("Discord-Bot bereit als %s", self.user)
        runtime.logger.log("info", "discord", "Discord-Bot bereit", {"user": str(self.user)})
        if not hasattr(self, "_reminder_task"):
            self._reminder_task = asyncio.create_task(self._reminder_loop())

    async def on_message(self, message: discord.Message) -> None:
        is_dm = isinstance(message.channel, discord.DMChannel)
        author_id = str(message.author.id)
        allowed_user = author_id == str(runtime.settings.discord_user_id)
        allowed_test_bot = (
            message.author.bot
            and runtime.settings.discord_allow_test_bots
            and author_id == str(runtime.settings.discord_test_user_id)
        )
        allowed_test_channel = (
            allowed_test_bot
            and runtime.settings.discord_test_channel_id
            and str(message.channel.id) == str(runtime.settings.discord_test_channel_id)
        )
        if message.author.bot and not allowed_test_bot:
            return
        if not ((is_dm and (allowed_user or allowed_test_bot)) or allowed_test_channel):
            runtime.logger.log(
                "warn",
                "security",
                "Discord-Nachricht ignoriert",
                {"author_id": author_id, "is_dm": is_dm, "channel_id": str(message.channel.id)},
            )
            log.warning("Discord-Nachricht ignoriert: author_id=%s is_dm=%s", message.author.id, is_dm)
            return
        log.info("Discord-DM von erlaubtem Absender empfangen")
        source = "discord_testbot" if allowed_test_bot else "discord"
        async with message.channel.typing():
            answer = await runtime.agent.handle_message(message.content, source=source)
        await _send_answer(message.channel, answer)

    async def _reminder_loop(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            rows = runtime.memory.conn.execute(
                "SELECT * FROM reminders WHERE done = 0 AND due_at <= ? ORDER BY due_at ASC",
                (datetime.utcnow().isoformat(),),
            ).fetchall()
            for row in rows:
                user = await self.fetch_user(int(runtime.settings.discord_user_id))
                await user.send(f"Reminder: {row['text']}")
                runtime.memory.conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (row["id"],))
                runtime.memory.conn.commit()
                runtime.logger.log("info", "reminder", "Discord-Reminder gesendet", {"text": row["text"]})
            await asyncio.sleep(10)


async def main() -> None:
    if not runtime.settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN fehlt.")
    intents = discord.Intents.default()
    intents.message_content = True
    client = RedClawClient(intents=intents)
    await client.start(runtime.settings.discord_token)


async def _send_answer(channel: discord.abc.Messageable, answer: str) -> None:
    visible, attachment_paths = _extract_attachments(answer)
    visible = visible or "Erledigt."
    for chunk in _discord_chunks(visible):
        await channel.send(chunk)
    for path in attachment_paths:
        if not path.exists() or not path.is_file():
            await channel.send(f"Datei konnte nicht gesendet werden, weil sie nicht mehr existiert: {path}")
            continue
        size = path.stat().st_size
        if size > MAX_DISCORD_ATTACHMENT_BYTES:
            mb = size / (1024 * 1024)
            limit = MAX_DISCORD_ATTACHMENT_BYTES // (1024 * 1024)
            await channel.send(f"Datei ist zu groß für Discord: {path} ({mb:.1f} MB, Limit {limit} MB)")
            continue
        try:
            await channel.send(file=discord.File(path))
        except Exception as exc:
            log.exception("Discord-Datei konnte nicht gesendet werden: %s", path)
            await channel.send(f"Discord konnte die Datei nicht hochladen: {path} ({exc})")


def _extract_attachments(answer: str) -> tuple[str, list[Path]]:
    attachment_paths: list[Path] = []
    visible_lines: list[str] = []
    for line in answer.splitlines():
        if line.startswith(ATTACH_MARKER):
            attachment_paths.append(Path(line.removeprefix(ATTACH_MARKER).strip()))
        else:
            visible_lines.append(line)
    visible = "\n".join(visible_lines).strip() or "Erledigt."
    return visible, attachment_paths


def _discord_chunks(text: str, size: int = 1900) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        if len(current) + len(line) + 1 > size:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}".strip()
    if current:
        chunks.append(current)
    return chunks


if __name__ == "__main__":
    asyncio.run(main())
