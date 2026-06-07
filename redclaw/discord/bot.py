from __future__ import annotations

import asyncio
from datetime import datetime
import logging

import discord

from redclaw.bootstrap import get_runtime


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
        if message.author.bot:
            return
        is_dm = isinstance(message.channel, discord.DMChannel)
        allowed_user = str(message.author.id) == str(runtime.settings.discord_user_id)
        if not is_dm or not allowed_user:
            runtime.logger.log(
                "warn",
                "security",
                "Discord-Nachricht ignoriert",
                {"author_id": str(message.author.id), "is_dm": is_dm},
            )
            log.warning("Discord-Nachricht ignoriert: author_id=%s is_dm=%s", message.author.id, is_dm)
            return
        log.info("Discord-DM von Redcrafter empfangen")
        async with message.channel.typing():
            answer = await runtime.agent.handle_message(message.content, source="discord")
        await message.channel.send(answer[:1900])

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


if __name__ == "__main__":
    asyncio.run(main())
