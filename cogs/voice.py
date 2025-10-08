"""Voice commands and TTS playback."""

from __future__ import annotations

import asyncio

import discord
from discord.ext import commands


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx = bot.ctx
        self.listen_tasks: dict[int, asyncio.Task] = {}

    def get_voice_client(self, guild: discord.Guild | None) -> discord.VoiceClient | None:
        if not guild:
            return None
        return discord.utils.get(self.bot.voice_clients, guild=guild)

    @commands.command(name="voicechat")
    async def voicechat(self, ctx: commands.Context) -> None:
        if not ctx.author.voice:
            await ctx.send("You need to join a voice channel first!")
            return
        voice_client = self.get_voice_client(ctx.guild)
        if voice_client and voice_client.is_connected():
            await ctx.send("Already connected to a voice channel in this server.")
            return
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🎤 **Connor joined voice chat!** Use `!speak <message>` to make me talk.")

    @commands.command(name="leave")
    async def leave(self, ctx: commands.Context) -> None:
        voice_client = self.get_voice_client(ctx.guild)
        disconnected = False
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            disconnected = True
        if ctx.guild and ctx.guild.id in self.listen_tasks:
            self.listen_tasks[ctx.guild.id].cancel()
            del self.listen_tasks[ctx.guild.id]
        if disconnected:
            await ctx.send("👋 **Connor left the voice channel.**")
        else:
            await ctx.send("Not connected to any voice channel.")

    @commands.command(name="speak")
    async def speak(self, ctx: commands.Context, *, message: str) -> None:
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel first!")
            return
        voice_client = self.get_voice_client(ctx.guild)
        if not voice_client or not voice_client.is_connected():
            await ctx.send("I'm not connected to a voice channel! Use `!voicechat` first.")
            return
        if not self.ctx.voice.available:
            await ctx.send("❌ TTS engine not available!")
            return
        await ctx.send(f"🗣️ **Connor is speaking**: {message}")
        await self.ctx.voice.speak(voice_client, message)
        await ctx.send("✅ **Connor finished speaking**")

    @commands.command(name="respond")
    async def respond(self, ctx: commands.Context, *, user_message: str) -> None:
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel first!")
            return
        voice_client = self.get_voice_client(ctx.guild)
        if not voice_client or not voice_client.is_connected():
            await ctx.send("I'm not connected to a voice channel! Use `!voicechat` first.")
            return

        username = self.ctx.conversation.get_username(ctx.author)
        reply = await self.ctx.llm.generate_direct_reply(
            user_message,
            self.ctx.state.core_agent_statement,
            self.ctx.state.beliefs,
            username,
            self.ctx.state.current_age,
        )
        await ctx.send(f"**You said**: {user_message}\n**Connor will respond**: {reply}")
        if self.ctx.voice.available:
            await self.ctx.voice.speak(voice_client, reply)
            await ctx.send("✅ **Connor finished responding**")

    @commands.command(name="testvoice")
    async def testvoice(self, ctx: commands.Context) -> None:
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel!")
            return
        voice_client = self.get_voice_client(ctx.guild)
        if not voice_client or not voice_client.is_connected():
            await ctx.send("Not connected to voice. Use `!voicechat` first.")
            return
        if not self.ctx.voice.available:
            await ctx.send("❌ TTS engine not available!")
            return
        await ctx.send("🔊 **Testing Voice System**")
        await self.ctx.voice.speak(voice_client, "Hello! This is Connor testing the voice system.")
        await ctx.send("✅ **Voice test successful!**")

    @commands.command(name="listen")
    async def listen(self, ctx: commands.Context) -> None:
        if not ctx.author.voice:
            await ctx.send("You need to join a voice channel first!")
            return

        voice_client = self.get_voice_client(ctx.guild)
        if voice_client and voice_client.is_connected():
            await ctx.send("Already connected to a voice channel in this server.")
        else:
            voice_client = await ctx.author.voice.channel.connect()

        await ctx.send("🎤 **Connor joined voice and is listening!**")
        await ctx.send("🗣️ **Just speak normally!** Connor will respond after a moment.")
        await ctx.send("🔊 **Voice Commands**:\n• Just talk normally\n• `!speak <message>` - Make Connor speak\n• `!leave` - Make Connor leave voice channel")

        if ctx.guild:
            if ctx.guild.id in self.listen_tasks:
                self.listen_tasks[ctx.guild.id].cancel()
            task = self.bot.loop.create_task(self.listen_loop(ctx, voice_client))
            self.listen_tasks[ctx.guild.id] = task

    async def listen_loop(self, ctx: commands.Context, voice_client: discord.VoiceClient) -> None:
        try:
            while voice_client and voice_client.is_connected():
                await asyncio.sleep(15)
                simulated_text = "Hello Connor, how are you today?"
                username = self.ctx.conversation.get_username(ctx.author)
                reply = await self.ctx.llm.generate_direct_reply(
                    simulated_text,
                    self.ctx.state.core_agent_statement,
                    self.ctx.state.beliefs,
                    username,
                    self.ctx.state.current_age,
                )
                await ctx.send(f"**Connor heard**: {simulated_text}\n**Connor responds**: {reply}")
                if self.ctx.voice.available:
                    await self.ctx.voice.speak(voice_client, reply)
                self.ctx.storage.add_chat_interaction(username, f"[Voice] {simulated_text}", reply, self.ctx.state.core_agent_statement)
        except asyncio.CancelledError:
            pass
