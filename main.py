"""Entry point and bot creation."""

from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from .config import load_settings
from .context import ConnorContext, build_context
from .cogs import register_cogs


class ConnorBot(commands.Bot):
    def __init__(self, ctx: ConnorContext):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.ctx = ctx

    async def close(self) -> None:
        await super().close()
        await self.ctx.llm.close()


def create_bot() -> ConnorBot:
    settings = load_settings()
    ctx = build_context(settings)
    bot = ConnorBot(ctx)
    register_cogs(bot)
    return bot


def run() -> None:
    bot = create_bot()
    bot.run(bot.ctx.settings.discord_token)


if __name__ == "__main__":
    run()
