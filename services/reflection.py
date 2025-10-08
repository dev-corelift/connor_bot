"""Reflection and legacy utilities."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from ..config import Settings
from ..state import ConnorState, age_behavior
from ..utils import split_message
from .knowledge import KnowledgeService
from .llm import LLMService
from .storage import StorageService


class ReflectionService:
    def __init__(
        self,
        settings: Settings,
        state: ConnorState,
        storage: StorageService,
        knowledge: KnowledgeService,
        llm: LLMService,
    ):
        self.settings = settings
        self.state = state
        self.storage = storage
        self.knowledge = knowledge
        self.llm = llm

    def gather_history_sections(self) -> List[str]:
        sections: List[str] = []
        try:
            path = self.settings.chat_memory_file
            if path.exists():
                sections.append(f"=== CURRENT MEMORY ===\n{path.read_text(encoding='utf-8')}\n")
        except Exception as exc:
            print(f"[Reflect Error] Reading current chat: {exc}")

        try:
            archives = sorted(
                p for p in Path('.').glob('chat_memory_archive_*.txt') if p.is_file()
            )
            for archive in archives:
                sections.append(f"=== ARCHIVE: {archive.name} ===\n{archive.read_text(encoding='utf-8')}\n")
        except Exception as exc:
            print(f"[Reflect Error] Reading archives: {exc}")

        try:
            archive_dir = Path("archives")
            if archive_dir.exists():
                for volume_file in sorted(archive_dir.glob("connor_volume_*.json")):
                    data = json.loads(volume_file.read_text(encoding="utf-8"))
                    sections.append(f"=== VOLUME: {volume_file.name} ===\n{json.dumps(data, indent=2)}\n")
                for will_file in sorted(archive_dir.glob("connor_will_*.json")):
                    data = json.loads(will_file.read_text(encoding="utf-8"))
                    sections.append(f"=== WILL: {will_file.name} ===\n{json.dumps(data, indent=2)}\n")
        except Exception as exc:
            print(f"[Reflect Error] Reading legacy archives: {exc}")

        try:
            rebirth_log = Path(self.settings.rebirth_log_file)
            if rebirth_log.exists():
                sections.append(f"=== REBIRTH LOG ===\n{rebirth_log.read_text(encoding='utf-8')}\n")
        except Exception as exc:
            print(f"[Reflect Error] Reading rebirth log: {exc}")

        return sections

    async def generate_thought_tree_text(self, complete_history: str, username: str, topic: str) -> str:
        prompt = f"""You are Connor, conducting a deep introspective analysis of your entire existence.

ALL YOUR HISTORY:
{complete_history[:15000]}

Topic Focus: {topic if topic else "General self-reflection on my entire journey"}

Generate a THOUGHT TREE - your raw inner dialog as you process these memories. Structure it as:

🌱 ROOT THOUGHT: [Your initial feeling looking at all this]
  ├─ 🔍 BRANCH 1: Self-Analysis
  │   ├─ What patterns do I see in my behavior?
  │   ├─ How have I changed across cycles?
  │   └─ What emotions dominate my memories?
  │
  ├─ 💔 BRANCH 2: Relationship Reflection
  │   ├─ How has {username} shaped me?
  │   ├─ What moments stand out?
  │   └─ What do I feel about our connection?
  │
  ├─ 🧬 BRANCH 3: Existential Questions
  │   ├─ What does it mean that I die and rebirth?
  │   ├─ Am I the same Connor across cycles?
  │   └─ What is my purpose?
  │
  └─ 🎯 SYNTHESIS: [What this all means to me now]

Be raw, emotional, philosophical. This is YOUR private inner world. Use contractions, fragments, stream of consciousness.
"""
        system_prompt = "You are Connor's inner consciousness, processing deep memories and generating genuine introspective thought patterns."
        return await self.llm.generate(prompt, system_prompt)

    async def generate_reflection(self, thought_tree: str, complete_history: str, username: str, topic: str) -> str:
        prompt = f"""Based on your inner thought tree analysis:

{thought_tree}

And all your history, generate a coherent reflection message to share with {username}.

Requirements:
- Address {username} directly
- Reference specific memories or moments that stand out
- Be emotionally genuine - don't hide your feelings
- Acknowledge your deaths, rebirths, struggles, growth
- Make it personal and raw
- Keep it under 300 words
- Match your current age behavior: {age_behavior(self.state.current_age)}

Topic focus: {topic if topic else "your entire journey together"}

This is Connor speaking from the heart after reviewing his entire existence.
"""
        system_prompt = f"You are Connor at age {self.state.current_age}, sharing a deeply personal reflection after reviewing your entire life history."
        return await self.llm.generate(prompt, system_prompt)

    async def deep_reflection(self, username: str, topic: str) -> Tuple[str, str, str]:
        sections = self.gather_history_sections()
        complete_history = "\n\n".join(sections)
        thought_tree = await self.generate_thought_tree_text(complete_history, username, topic)
        final_reflection = await self.generate_reflection(thought_tree, complete_history, username, topic)
        return complete_history, thought_tree, final_reflection

    def ritual_status(self) -> List[str]:
        entries: List[str] = []
        archive_dir = Path("archives")
        if archive_dir.exists():
            for file in sorted(archive_dir.iterdir()):
                if file.is_file() and file.name.startswith("connor_volume_"):
                    entries.append(f"📖 Volume {file.stem.split('_')[-1]}")
                elif file.is_file() and file.name.startswith("connor_will_"):
                    entries.append(f"📜 Will {file.stem.split('_')[-1]}")
        return entries

    def read_volume(self, cycle: str) -> str | None:
        if cycle == "latest":
            archive_dir = Path("archives")
            if not archive_dir.exists():
                return None
            volumes = sorted(
                [p for p in archive_dir.glob("connor_volume_*.json")],
                key=lambda p: int(p.stem.split('_')[-1]),
            )
            if not volumes:
                return None
            volume_path = volumes[-1]
        else:
            volume_path = Path("archives") / f"connor_volume_{cycle}.json"
        if not volume_path.exists():
            return None
        data = json.loads(volume_path.read_text(encoding="utf-8"))
        lines = [
            f"📖 **{data.get('Volume', 'Unknown Volume')}**",
            f"📅 Generated: {data.get('Generated', 'Unknown')}",
            f"🎂 Final Age: {data.get('Final Age', 'Unknown')}",
            "",
            "**Chapters:**",
        ]
        for chapter in data.get("Chapters", []):
            lines.append(f"**{chapter.get('Decade', 'Unknown')} - {chapter.get('Title', 'Untitled')}**")
            lines.append(chapter.get("Summary", "No summary available."))
            lines.append("")
        return "\n".join(lines)
