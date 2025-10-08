"""Voice synthesis and playback."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import discord

from ..config import Settings


class VoiceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._tts_engine = self._init_tts()
        self._lock = asyncio.Lock()

    def _init_tts(self):
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self.settings.tts_rate)
            engine.setProperty("volume", self.settings.tts_volume)
            return engine
        except Exception as exc:
            print(f"[TTS Init Error] {exc}")
            return None

    @property
    def available(self) -> bool:
        return self._tts_engine is not None

    async def synthesize(self, text: str, outfile: Path) -> Optional[Path]:
        if not self._tts_engine:
            return None

        loop = asyncio.get_running_loop()

        def _save():
            self._tts_engine.save_to_file(text, str(outfile))
            self._tts_engine.runAndWait()

        async with self._lock:
            await loop.run_in_executor(None, _save)

        if outfile.exists():
            return outfile
        return None

    async def speak(self, voice_client: discord.VoiceClient, text: str) -> bool:
        if not voice_client or not voice_client.is_connected():
            return False

        temp_path = Path("temp_voice_tts.wav")
        audio_path = await self.synthesize(text, temp_path)
        if not audio_path:
            return False

        try:
            source = discord.FFmpegPCMAudio(str(audio_path))
            voice_client.play(source)
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
            return True
        except discord.ClientException as exc:
            print(f"[Voice Client Error] {exc}")
            return False
        finally:
            try:
                if audio_path.exists():
                    os.unlink(audio_path)
            except OSError as exc:
                print(f"[Voice Cleanup Error] {exc}")
