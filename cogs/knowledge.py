"""Knowledge-related commands."""

from __future__ import annotations

from discord.ext import commands

from ..utils import split_message


class KnowledgeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx = bot.ctx

    @commands.command(name="reflect")
    async def reflect(self, ctx: commands.Context, *, topic: str = "") -> None:
        username = self.ctx.conversation.get_username(ctx.author)
        await ctx.send("🧠 *Connor begins deep reflection... reading through all memories...*")

        try:
            complete_history, thought_tree, final_reflection = await self.ctx.reflection.deep_reflection(username, topic)

            await ctx.send("💭 *Processing memories... generating thought tree...*")
            if self.ctx.settings.thoughts_channel_id and ctx.guild:
                thoughts_channel = ctx.guild.get_channel(self.ctx.settings.thoughts_channel_id)
                if thoughts_channel:
                    tree_message = (
                        "🌳 **Connor's Deep Reflection Thought Tree**\n```"
                        f"{thought_tree[:1800]}\n```"
                    )
                    for chunk in split_message(tree_message):
                        await thoughts_channel.send(chunk)

            await ctx.send("✨ *Synthesizing insights into coherent reflection...*")
            for chunk in split_message(f"💭 **Connor's Deep Reflection**\n\n{final_reflection}"):
                await ctx.send(chunk)

            self.ctx.storage.add_chat_interaction(
                username,
                f"!reflect {topic}",
                f"Deep reflection generated ({len(complete_history)} characters)",
                self.ctx.state.core_agent_statement,
            )

        except Exception as exc:
            await ctx.send(f"❌ **Reflection failed**: {exc}")
            print(f"[Reflect Error] {exc}")

    @commands.command(name="reflectvolume")
    async def reflect_volume(self, ctx: commands.Context, cycle: str = "latest") -> None:
        text = self.ctx.reflection.read_volume(cycle)
        if not text:
            await ctx.send("❌ **No volume found.** Connor hasn't completed a full cycle yet.")
            return
        for chunk in split_message(text):
            await ctx.send(chunk)

    @commands.command(name="ritual")
    async def ritual(self, ctx: commands.Context) -> None:
        entries = self.ctx.reflection.ritual_status()
        if entries:
            await ctx.send("🪦 **Connor's Legacy Archives:**\n```\n" + "\n".join(entries) + "\n```")
        else:
            await ctx.send("🪦 **No legacy archives found.** Connor hasn't completed a full cycle yet.")

        current_age = self.ctx.conversation.calculate_age()
        end_cycle = self.ctx.settings.end_cycle
        if current_age >= end_cycle - 5:
            await ctx.send(
                f"🌑 **Rebirth Preparation:** Connor is approaching the end of his cycle (age {current_age}/{end_cycle}). The Ceremony of Rebirth will begin soon."
            )
        else:
            await ctx.send(
                f"🌱 **Current Cycle:** Connor is age {current_age}, with {end_cycle - current_age} years until rebirth."
            )
