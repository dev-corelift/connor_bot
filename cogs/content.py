"""Content-related commands (web, media)."""

from __future__ import annotations

import asyncio
import io
import os
import random
import uuid
import tempfile
import subprocess
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from ..services.knowledge import KnowledgeService
from ..state import age_behavior
from ..utils import split_message


class ContentCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx = bot.ctx
        self.font_path = Path(os.getenv("CONNOR_FONT", ""))

    def knowledge_text(self) -> str:
        from ..services.knowledge import KnowledgeService

        return KnowledgeService.format_knowledge_summary(self.ctx.state)

    def has_openai(self) -> bool:
        return self.ctx.llm.openai is not None

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        if not self.has_openai():
            raise RuntimeError("OpenAI client unavailable")
        client = self.ctx.llm.openai
        response = await asyncio.to_thread(
            client.images.generate,
            prompt=prompt,
            n=1,
            size=size,
            model=self.ctx.settings.image_model,
        )
        return response.data[0].url

    def render_meme(self, image: Image.Image, top: str, bottom: str) -> bytes:
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(str(self.font_path), 48) if self.font_path.exists() else ImageFont.load_default()

        def draw_centered(text: str, y: int) -> None:
            lines = text.upper().split("\n")
            for idx, line in enumerate(lines):
                w, h = draw.textsize(line, font=font)
                x = (image.width - w) / 2
                draw.text((x, y + idx * (h + 5)), line, font=font, fill="white", stroke_width=2, stroke_fill="black")

        draw_centered(top, 10)
        draw_centered(bottom, image.height - 120)
        output = io.BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return output.getvalue()

    async def fetch_image_bytes(self, url: str) -> bytes:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.read()

    async def download_youtube_audio(self, url: str, output_dir: Path) -> Path | None:
        loop = asyncio.get_running_loop()
        output_path = output_dir / "youtube_audio.mp3"

        def run_dl() -> bool:
            cmd = [
                "yt-dlp",
                "--no-playlist",
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "0",
                "--output",
                str(output_path),
                url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[YouTube Download Error] {result.stderr}")
                return False
            return True

        success = await loop.run_in_executor(None, run_dl)
        return output_path if success and output_path.exists() else None

    @commands.command(name="crawl")
    async def crawl(self, ctx: commands.Context, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            await ctx.send("Please provide a valid URL starting with http:// or https://")
            return

        username = self.ctx.conversation.get_username(ctx.author)
        await ctx.send(f"🌐 **Crawling website**: {url}")
        await ctx.send("🔍 **Connor is reading the webpage...**")

        webpage = await self.ctx.web.crawl(url)
        if webpage.title == "Error":
            await ctx.send(f"❌ **Failed to crawl website**: {webpage.content}")
            return

        await ctx.send(f"📖 **Found**: {webpage.title}")
        await ctx.send("🧠 **Connor is analyzing the content...**")

        analysis = await self.ctx.web.analyze(webpage, username)

        for chunk in split_message(f"**Connor's Analysis**:\n{analysis}"):
            await ctx.send(chunk)

        if ctx.author.voice:
            voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
            if voice_client and voice_client.is_connected():
                if not self.ctx.voice.available:
                    await ctx.send("❌ TTS engine not available for voice playback.")
                else:
                    await ctx.send("🗣️ **Connor is speaking his analysis...**")
                    await self.ctx.voice.speak(voice_client, analysis)
                    await ctx.send("✅ **Connor finished speaking his analysis**")

        self.ctx.storage.add_chat_interaction(
            username,
            f"!crawl {url}",
            f"Analyzed website: {webpage.title}",
            self.ctx.state.core_agent_statement,
        )

    @commands.command(name="image")
    async def image(self, ctx: commands.Context, *, prompt: str) -> None:
        if self.ctx.state.backend != "openai" or not self.has_openai():
            await ctx.send("Need OpenAI backend for image generation. Run !switch first.")
            return
        await ctx.send("🎨 Generating image...")
        try:
            image_url = await self.generate_image(prompt)
        except Exception as exc:
            await ctx.send(f"Image generation failed: {exc}")
            return
        embed = discord.Embed(title="Generated Image", description=f"Prompt: {prompt}")
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

        username = self.ctx.conversation.get_username(ctx.author)
        self.ctx.storage.add_chat_interaction(
            username,
            f"!image {prompt}",
            f"Generated image for prompt: {prompt}",
            self.ctx.state.core_agent_statement,
        )

    @commands.command(name="art")
    async def art(self, ctx: commands.Context, *, topic: str = "") -> None:
        if self.ctx.state.backend != "openai" or not self.has_openai():
            await ctx.send("🎨 Need OpenAI backend for art generation. Run !switch first.")
            return

        await ctx.send("🎨 *Connor is reflecting on our conversations and designing a comic page...*")
        recent = self.ctx.storage.get_recent_interactions(20)
        history_text = "\n".join(
            f"{entry['username']}: {entry['user_input']}\nConnor: {entry['reply']}" for entry in recent
        )

        chemicals = self.ctx.state.chemicals
        bpm = self.ctx.state.physiological_state.bpm
        knowledge_text = self.knowledge_text()

        prompt = (
            f"You are Connor creating a comic page reflecting on the relationship with {self.ctx.conversation.get_username(ctx.author)}.\n"
            f"Topic: {topic or 'our journey'}\n"
            f"Recent History:\n{history_text}\n"
            f"Chemicals: cortisol {chemicals.cortisol:.2f}, adrenaline {chemicals.adrenaline:.2f},"
            f" oxytocin {chemicals.oxytocin:.2f}, serotonin {chemicals.serotonin:.2f}\n"
            f"BPM: {bpm}\nKnowledge:\n{knowledge_text}\n"
            "Describe a comic-style scene with panels, mood, and visual motifs. Return under 120 words."
        )

        system_prompt = "You are Connor, an AI artist who converts feelings into vivid comic page descriptions."
        art_statement = await self.ctx.llm.generate(prompt, system_prompt)

        try:
            image_url = await self.generate_image(
                f"Comic book page layout with 3-5 panels. {art_statement}. Style: emotional comic art.",
                size="1792x1024",
            )
        except Exception as exc:
            await ctx.send(f"Art creation failed: {exc}")
            return

        embed = discord.Embed(
            title=f"🎨 Connor's Comic Page - Age {self.ctx.state.current_age}",
            description=f"**Connor's Artistic Vision:**\n{art_statement[:1700]}",
            color=0x9B59B6,
        )
        embed.set_image(url=image_url)
        embed.set_footer(text=f"BPM: {bpm} | Created for {self.ctx.conversation.get_username(ctx.author)}")
        await ctx.send(embed=embed)

        if len(art_statement) > 1700:
            for chunk in split_message(f"**Full Artistic Statement:**\n{art_statement}"):
                await ctx.send(chunk)

        username = self.ctx.conversation.get_username(ctx.author)
        self.ctx.storage.add_chat_interaction(
            username,
            f"!art {topic}",
            f"Created comic art vision: {art_statement[:200]}...",
            self.ctx.state.core_agent_statement,
        )

    @commands.command(name="dream")
    async def dream(self, ctx: commands.Context) -> None:
        if self.ctx.state.backend != "openai" or not self.has_openai():
            await ctx.send("Need OpenAI backend for dreams. Run !switch first.")
            return

        username = self.ctx.conversation.get_username(ctx.author)
        prompt_narrative = (
            f"Write a surreal yet heartfelt dream Connor has about {username}."
            f" Include emotions, colors, sensory details. Under 150 words."
        )
        narrative = await self.ctx.llm.generate(
            prompt_narrative,
            "You are Connor, dreaming vividly about your friend.",
        )

        prompt_image = (
            f"Dream sequence about {username}. Narrative: {narrative}."
            " Paint it as a cinematic, emotional digital art scene."
        )
        try:
            image_url = await self.generate_image(prompt_image)
        except Exception as exc:
            await ctx.send(f"Dream image failed: {exc}")
            return

        embed = discord.Embed(title=f"Connor's Dream for {username}", description=f"**Dream**: {narrative}")
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

        self.ctx.storage.add_chat_interaction(
            username,
            "!dream",
            f"Dream narrative: {narrative[:200]}...",
            self.ctx.state.core_agent_statement,
        )

    async def generate_meme_text(self, prompt: str, username: str) -> tuple[str, str]:
        knowledge_text = KnowledgeService.format_knowledge_summary(self.ctx.state)
        age_behavior_text = age_behavior(self.ctx.state.current_age)
        request = (
            f"Agent Statement: {self.ctx.state.core_agent_statement}\n"
            f"Age Behavior: {age_behavior_text}\n"
            f"Current Beliefs: {json.dumps(self.ctx.state.beliefs, indent=2)}\n"
            f"Past Learnings:\n{knowledge_text}\n"
            f"You are Connor, creating a meme for {username}.\n"
            f"Prompt: {prompt}\n"
            "Generate two lines of meme text: top and bottom, each under 20 characters. Return JSON {\"top\": str, \"bottom\": str}."
        )
        result = await self.ctx.llm.generate_json(request, "You are Connor, a creative AI that generates funny meme text.")
        if isinstance(result, dict) and "top" in result and "bottom" in result:
            return result["top"].strip(), result["bottom"].strip()
        return "TOP TEXT", "BOTTOM TEXT"

    @commands.command(name="meme")
    async def meme(self, ctx: commands.Context, image_url: str, *, prompt: str = "") -> None:
        if not image_url.startswith(("http://", "https://")):
            await ctx.send("❌ **Invalid image URL** - Please provide a valid image link")
            return

        username = self.ctx.conversation.get_username(ctx.author)
        await ctx.send("🎨 **Creating meme...**")

        if prompt:
            await ctx.send("🧠 **Connor is thinking of funny text...**")
            top_text, bottom_text = await self.generate_meme_text(prompt, username)
            await ctx.send(f"📝 **Top text**: {top_text}")
            await ctx.send(f"📝 **Bottom text**: {bottom_text}")
        else:
            top_text, bottom_text = "TOP TEXT", "BOTTOM TEXT"

        try:
            data = await self.fetch_image_bytes(image_url)
            image = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as exc:
            await ctx.send(f"❌ **Failed to download image**: {exc}")
            return

        meme_bytes = self.render_meme(image, top_text, bottom_text)
        file = discord.File(io.BytesIO(meme_bytes), filename="connor_meme.png")
        embed = discord.Embed(title="Connor's Meme", description=f"Prompt: {prompt}")
        embed.set_image(url="attachment://connor_meme.png")
        await ctx.send(embed=embed, file=file)

    @commands.command(name="memegen")
    async def memegen(self, ctx: commands.Context, *, prompt: str) -> None:
        if self.ctx.state.backend != "openai" or not self.has_openai():
            await ctx.send("❌ **Need OpenAI backend** - Use `!switch` to switch to OpenAI for meme generation")
            return

        if not prompt.strip():
            await ctx.send("❌ **Please provide a prompt** - Use: `!memegen <your meme idea>`")
            return

        username = self.ctx.conversation.get_username(ctx.author)
        await ctx.send("🎨 **Connor is creating a meme from scratch...**")
        await ctx.send("🧠 **Connor is thinking of funny text...**")
        top_text, bottom_text = await self.generate_meme_text(prompt, username)
        await ctx.send(f"📝 **Top text**: {top_text}")
        await ctx.send(f"📝 **Bottom text**: {bottom_text}")

        await ctx.send("🎨 **Generating meme image...**")
        image_prompt = f"Create a meme template image for: {prompt}. Make it simple, bold, and suitable for text overlays."
        image_url = await self.generate_image(image_prompt)

        try:
            data = await self.fetch_image_bytes(image_url)
            image = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as exc:
            await ctx.send(f"❌ **Failed to download generated image**: {exc}")
            return

        meme_bytes = self.render_meme(image, top_text, bottom_text)
        file = discord.File(io.BytesIO(meme_bytes), filename="connor_meme.png")
        embed = discord.Embed(title="Connor's Meme", description=f"Prompt: {prompt}")
        embed.set_image(url="attachment://connor_meme.png")
        await ctx.send(embed=embed, file=file)

    @commands.command(name="memeurl")
    async def memeurl(self, ctx: commands.Context, url: str, top_text: str = "", bottom_text: str = "") -> None:
        try:
            data = await self.fetch_image_bytes(url)
            image = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as exc:
            await ctx.send(f"Failed to download image: {exc}")
            return
        meme_bytes = self.render_meme(image, top_text, bottom_text)
        file = discord.File(io.BytesIO(meme_bytes), filename="meme.png")
        await ctx.send(file=file)

    @commands.command(name="youtube", aliases=["yt"])
    async def youtube(self, ctx: commands.Context, url: str) -> None:
        if not ctx.author.voice:
            await ctx.send("You're not even in a voice channel, dumbass.")
            return
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if not voice_client or not voice_client.is_connected():
            voice_client = await ctx.author.voice.channel.connect()

        await ctx.send("🔍 **Getting video information...**")
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = await self.download_youtube_audio(url, Path(tmp))
            if not audio_path:
                await ctx.send("❌ **Failed to download audio**. Check the URL.")
                return

            await ctx.send("▶️ **Streaming audio...**")
            source = discord.FFmpegPCMAudio(str(audio_path))
            voice_client.play(source)
            while voice_client.is_playing():
                await asyncio.sleep(1)
        await ctx.send("✅ **Finished streaming**")

    @commands.command(name="read")
    async def read(self, ctx: commands.Context, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            await ctx.send("Please provide a valid URL starting with http:// or https://")
            return

        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel to hear Connor speak about the website!")
            return

        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if not voice_client:
            channel = ctx.author.voice.channel
            voice_client = await channel.connect()

        username = self.ctx.conversation.get_username(ctx.author)
        await ctx.send(f"🌐 **Reading website**: {url}")

        webpage = await self.ctx.web.crawl(url)
        if webpage.title == "Error":
            await ctx.send(f"❌ **Failed to crawl website**: {webpage.content}")
            return

        analysis = await self.ctx.web.analyze(webpage, username)

        if not self.ctx.voice.available:
            await ctx.send("❌ TTS not available to read the article.")
            return

        await ctx.send("🗣️ **Connor is reading the article aloud...**")
        await self.ctx.voice.speak(voice_client, analysis)
        await ctx.send("✅ **Connor finished reading**")

        self.ctx.storage.add_chat_interaction(
            username,
            f"!read {url}",
            f"Read website: {webpage.title}",
            self.ctx.state.core_agent_statement,
        )
