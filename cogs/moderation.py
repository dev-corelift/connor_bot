"""Moderation utilities."""

from __future__ import annotations

import asyncio

import discord
from discord.ext import commands


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="nuke")
    async def nuke(self, ctx: commands.Context) -> None:
        if not ctx.channel.permissions_for(ctx.author).manage_messages:
            await ctx.send("You need `Manage Messages` permission to use this.")
            return

        embed = discord.Embed(
            title="💥 NUKE CONFIRMATION",
            description="This will delete **all** messages in this channel. Are you absolutely sure?",
            color=0xFF0000,
        )
        embed.set_footer(text="React with ✅ to confirm or ❌ to cancel within 30 seconds.")
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user == ctx.author
                and reaction.message.id == message.id
                and str(reaction.emoji) in {"✅", "❌"}
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("⏰ **NUKE TIMEOUT** - Command cancelled due to inactivity.")
            return

        if str(reaction.emoji) == "❌":
            await ctx.send("❌ **NUKE CANCELLED** - Channel remains untouched.")
            return

        deleted = 0
        async for msg in ctx.channel.history(limit=None):
            try:
                await msg.delete()
                deleted += 1
                await asyncio.sleep(0.1)
            except discord.Forbidden:
                continue
            except discord.NotFound:
                continue
        await ctx.send(f"💥 **NUKE COMPLETE** 💥\nDeleted **{deleted}** messages from this channel.")
