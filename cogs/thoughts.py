"""Thought tree commands."""

from __future__ import annotations

from discord.ext import commands

from ..utils import split_message


class ThoughtsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx = bot.ctx

    @commands.command(name="think")
    async def think(self, ctx: commands.Context, *, trigger: str) -> None:
        if not trigger.strip():
            await ctx.send("Yo, give me something to think about! Use: !think <your question or topic>")
            return
        tree, message = await self.ctx.thought.generate_tree(trigger)
        if not tree:
            await ctx.send(f"Couldn't start thinking: {message}")
            return

        self.ctx.storage.add_chat_interaction(
            self.ctx.conversation.get_username(ctx.author),
            f"!think {trigger}",
            f"Started thought tree: {tree.tree_id}",
            self.ctx.state.core_agent_statement,
        )

        await ctx.send(f"🌱 Started thinking about: {trigger}\nTree ID: `{tree.tree_id}`")

    @commands.command(name="expand")
    async def expand(self, ctx: commands.Context, tree_id: str, thought_id: str) -> None:
        nodes, message = await self.ctx.thought.expand_tree(tree_id, thought_id)
        if not nodes:
            await ctx.send(f"Couldn't expand that thought: {message}")
            return
        await ctx.send(f"🌿 Expanded thought with {len(nodes)} new branches")

    @commands.command(name="show")
    async def show_thoughts(self, ctx: commands.Context, tree_id: str) -> None:
        trees = self.ctx.thought.load_trees()
        tree = trees.get(tree_id)
        if not tree:
            await ctx.send("Thought tree not found.")
            return
        display = self.ctx.thought.format_tree(tree, max_depth=6)
        for chunk in split_message(display):
            await ctx.send(chunk)

    @commands.command(name="thoughts", aliases=["recentthoughts"])
    async def recent_thoughts(self, ctx: commands.Context) -> None:
        trees = self.ctx.thought.recent_trees()
        if not trees:
            await ctx.send("No thought trees yet. Try `!think <topic>`.")
            return
        lines = [self.ctx.thought.tree_summary(tree) for tree in trees]
        for chunk in split_message("\n".join(lines)):
            await ctx.send(chunk)

    @commands.command(name="autothink")
    async def autothink(self, ctx: commands.Context, *, trigger: str) -> None:
        message = await self.ctx.thought.auto_think(trigger)
        await ctx.send(f"🧠 {message}")

    @commands.command(name="brainstorm")
    async def massive_brain(self, ctx: commands.Context, *, trigger: str) -> None:
        tree = await self.ctx.thought.massive_brainstorm(trigger)
        if not tree:
            await ctx.send("Couldn't create massive brain, try again later.")
            return
        await ctx.send(
            f"🧠 **MASSIVE BRAIN COMPLETE** - Created huge thought tree about: {tree.trigger}\nTree ID: `{tree.tree_id}`\nTotal Thoughts: {len(tree.nodes)}"
        )
