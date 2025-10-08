"""Speech recognition utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - optional dependency
    WhisperModel = None  # type: ignore


class SpeechService:
    def __init__(self, model_size: str = "small"):
        self.model_size = model_size
        self.model: Optional[WhisperModel] = None
        self._load_model()

    def _load_model(self) -> None:
        if WhisperModel is None:
            print("[Whisper Init] faster_whisper not installed; speech features disabled")
            return
        try:
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        except Exception as exc:
            print(f"[Whisper Init Error] {exc}")
            self.model = None

    def transcribe(self, audio_path: Path) -> str:
        if not self.model or not audio_path.exists():
            return ""
        try:
            segments, _ = self.model.transcribe(str(audio_path), beam_size=5)
            return " ".join(segment.text for segment in segments).strip()
        except Exception as exc:
            print(f"[Whisper Transcription Error] {exc}")
            return ""
