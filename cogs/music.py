"""Music playback commands."""

from __future__ import annotations

import asyncio
import os
import random
from pathlib import Path

import discord
from discord.ext import commands

from ..utils import split_message


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx = bot.ctx
        self.music_playing = False
        self.music_task: asyncio.Task | None = None

    def cog_unload(self) -> None:
        if self.music_task and not self.music_task.done():
            self.music_task.cancel()

    def get_voice_client(self, guild: discord.Guild | None) -> discord.VoiceClient | None:
        if not guild:
            return None
        return discord.utils.get(self.bot.voice_clients, guild=guild)

    @commands.command(name="music")
    async def music(self, ctx: commands.Context) -> None:
        if self.music_playing:
            await ctx.send("Already jamming, chill the fuck out.")
            return
        if not ctx.author.voice:
            await ctx.send("You're not even in a voice channel, dumbass.")
            return

        music_folder = self.ctx.settings.music_folder
        if not music_folder.exists():
            await ctx.send("No music folder found. Add some tracks to the Music directory.")
            return

        voice_client = self.get_voice_client(ctx.guild)
        if not voice_client or not voice_client.is_connected():
            voice_client = await ctx.author.voice.channel.connect()

        self.music_playing = True
        self.music_task = asyncio.create_task(self.play_loop(ctx, voice_client, music_folder))
        await ctx.send("Alright, let's spin some random tracks... 🎵")

    async def play_loop(self, ctx: commands.Context, voice_client: discord.VoiceClient, folder: Path) -> None:
        try:
            played: list[Path] = []
            while self.music_playing:
                songs = [p for p in folder.iterdir() if p.suffix.lower() in {".mp3", ".wav", ".ogg"}]
                if not songs:
                    await ctx.send("No songs in the music folder. Add some .mp3 or .wav files.")
                    break
                available = [song for song in songs if song not in played]
                if not available:
                    played.clear()
                    available = songs
                song = random.choice(available)
                played.append(song)
                await ctx.send(f"Next up: `{song.name}`")

                lyrics = ""
                if self.ctx.speech.model:
                    lyrics = await asyncio.get_running_loop().run_in_executor(None, self.ctx.speech.transcribe, song)
                    if not lyrics:
                        lyrics = "[No lyrics detected—might be instrumental]"
                else:
                    lyrics = "[Whisper model not loaded]"

                if lyrics and not lyrics.startswith("["):
                    try:
                        prompt = (
                            f"These are the lyrics of a song you wrote: {lyrics}\n"
                            "Give me a short, creative DJ comment or emotional reflection based on these lyrics. Use no more than 25 words."
                        )
                        dj_comment = await self.ctx.llm.generate(
                            prompt, "You are Connor, a badass DJ AI with a knack for hype and emotion."
                        )
                        for chunk in split_message(f"**DJ Connor's Vibe Check**:\n{dj_comment}"):
                            await ctx.send(chunk)
                        if self.ctx.voice.available and voice_client.is_connected():
                            await self.ctx.voice.speak(voice_client, dj_comment)
                    except Exception as exc:
                        print(f"[LLM DJ Comment Error] {exc}")

                source = discord.FFmpegPCMAudio(str(song))
                voice_client.play(source)
                while voice_client.is_playing() and self.music_playing:
                    await asyncio.sleep(1)
                if not self.music_playing:
                    voice_client.stop()
                    break
        finally:
            self.music_playing = False

    @commands.command(name="skip")
    async def skip(self, ctx: commands.Context) -> None:
        voice_client = self.get_voice_client(ctx.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await ctx.send("⏭️ Skipped to next song!")
        else:
            await ctx.send("No music playing to skip, genius.")

    @commands.command(name="stopmusic")
    async def stopmusic(self, ctx: commands.Context) -> None:
        voice_client = self.get_voice_client(ctx.guild)
        self.music_playing = False
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
        await ctx.send("Music stopped. Peace out! 🎵")
