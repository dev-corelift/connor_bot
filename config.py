"""Configuration management for Connor bot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    discord_token: str
    main_channel_id: int = 0
    beliefs_channel_id: int = 0
    thoughts_channel_id: int = 0
    knowledge_channel_id: int = 0
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    image_model: str = "dall-e-3"
    vision_model: str = "gpt-4o"
    ollama_api_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    whisper_model: str = "small"
    tts_rate: int = 150
    tts_volume: float = 0.9
    agent_statement_file: Path = Path("agent_statement.txt")
    belief_file: Path = Path("beliefs.txt")
    chat_memory_file: Path = Path("chat_memory.txt")
    thoughts_file: Path = Path("thoughts.txt")
    knowledge_file: Path = Path("knowledge.txt")
    username_file: Path = Path("username.txt")
    rebirth_log_file: Path = Path("rebirth_log.txt")
    music_folder: Path = Path("Music")
    summary_interval: int = 40
    chat_memory_limit: int = 50
    recent_history_limit: int = 8
    depressive_hit_threshold: int = 50
    initial_age: int = 37
    rebirth_age: int = 10
    age_increment_hours: float = 0.5
    end_cycle: int = 80


def load_settings(env_file: str | None = ".env") -> Settings:
    if env_file:
        load_dotenv(env_file)

    import os

    discord_token = os.getenv("DISCORD_TOKEN")
    if not discord_token:
        raise RuntimeError("DISCORD_TOKEN is required to start the bot.")

    def int_env(name: str, default: int = 0) -> int:
        value = os.getenv(name)
        try:
            return int(value) if value else default
        except (TypeError, ValueError):
            return default

    def path_env(name: str, default: str) -> Path:
        value = os.getenv(name, default)
        return Path(value).expanduser()

    initial_age, rebirth_age, age_increment_hours, end_cycle = 37, 10, 0.5, 80
    try:
        from connor_config import AGING  # type: ignore

        initial_age = int(AGING.get("initial_age", initial_age))
        rebirth_age = int(AGING.get("rebirth_age", rebirth_age))
        age_increment_hours = float(AGING.get("age_increment_hours", age_increment_hours))
        end_cycle = int(AGING.get("end_cycle", end_cycle))
    except Exception:
        pass

    return Settings(
        discord_token=discord_token,
        main_channel_id=int_env("MAIN_CHANNEL_ID"),
        beliefs_channel_id=int_env("BELIEFS_CHANNEL_ID"),
        thoughts_channel_id=int_env("THOUGHTS_CHANNEL_ID"),
        knowledge_channel_id=int_env("KNOWLEDGE_CHANNEL_ID"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
        image_model=os.getenv("IMAGE_MODEL", "dall-e-3"),
        vision_model=os.getenv("VISION_MODEL", "gpt-4o"),
        ollama_api_url=os.getenv("OLLAMA_API_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "mistral"),
        whisper_model=os.getenv("WHISPER_MODEL", "small"),
        tts_rate=int_env("TTS_RATE", 150),
        tts_volume=float(os.getenv("TTS_VOLUME", "0.9")),
        agent_statement_file=path_env("AGENT_STATEMENT_FILE", "agent_statement.txt"),
        belief_file=path_env("BELIEF_FILE", "beliefs.txt"),
        chat_memory_file=path_env("CHAT_MEMORY_FILE", "chat_memory.txt"),
        thoughts_file=path_env("THOUGHTS_FILE", "thoughts.txt"),
        knowledge_file=path_env("KNOWLEDGE_FILE", "knowledge.txt"),
        username_file=path_env("USERNAME_FILE", "username.txt"),
        rebirth_log_file=path_env("REBIRTH_LOG_FILE", "rebirth_log.txt"),
        music_folder=path_env("MUSIC_FOLDER", "Music"),
        summary_interval=int_env("SUMMARY_INTERVAL", 40),
        chat_memory_limit=int_env("CHAT_MEMORY_LIMIT", 50),
        recent_history_limit=int_env("RECENT_HISTORY_LIMIT", 8),
        depressive_hit_threshold=int_env("DEPRESSIVE_HIT_THRESHOLD", 50),
        initial_age=initial_age,
        rebirth_age=rebirth_age,
        age_increment_hours=age_increment_hours,
        end_cycle=end_cycle,
    )
