"""Admin and backend switching commands."""

from __future__ import annotations

import aiohttp
import discord
from discord.ext import commands


class ModelSwitchView(discord.ui.View):
    def __init__(self, cog: "AdminCog", models: list[str]):
        super().__init__(timeout=60)
        self.cog = cog
        self.models = models
        self.add_item(discord.ui.Button(label="OpenAI (Turbo + Images)", emoji="🤖", style=discord.ButtonStyle.primary))
        self.children[0].callback = self.switch_to_openai

        for model in models[:24]:
            button = discord.ui.Button(label=f"Ollama - {model[:18]}", emoji="🏠", style=discord.ButtonStyle.secondary)
            button.callback = self.make_ollama_callback(model)
            self.add_item(button)

    async def switch_to_openai(self, interaction: discord.Interaction) -> None:
        self.cog.ctx.state.backend = "openai"
        self.cog.ctx.state.model = self.cog.ctx.settings.openai_model
        await interaction.response.send_message("Switched to OpenAI—turbo mode, pics unlocked! 🚀", ephemeral=True)
        self.stop()

    def make_ollama_callback(self, model: str):
        async def callback(interaction: discord.Interaction) -> None:
            self.cog.ctx.state.backend = "ollama"
            self.cog.ctx.state.model = model
            await interaction.response.send_message(f"Switched to Ollama - {model}. Local and cheap! 🏠", ephemeral=True)
            self.stop()

        return callback


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx = bot.ctx

    @commands.command(name="switch")
    async def switch_backend(self, ctx: commands.Context) -> None:
        models = await self.fetch_ollama_models()
        if not models:
            await ctx.send("No Ollama models found—start your local instance, dumbass.")
            return

        view = ModelSwitchView(self, models)
        embed = discord.Embed(
            title="🤖 Model Switcher",
            description=f"**Current:** {self.ctx.state.backend.title()} ({self.ctx.state.model})",
            color=0x00FF00,
        )
        embed.add_field(name="Available Models", value="Click a button below to switch models", inline=False)
        await ctx.send(embed=embed, view=view)

    async def fetch_ollama_models(self) -> list[str]:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.ctx.settings.ollama_api_url}/api/tags") as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as exc:
            print(f"[Ollama Tags Error] {exc}")
            return []
