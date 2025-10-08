"""Persona and rebirth management."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from ..config import Settings
from ..state import ConnorState, age_behavior
from .knowledge import KnowledgeService
from .llm import LLMService
from .storage import StorageService


class PersonaService:
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

    async def generate_agent_statement(self) -> str:
        knowledge_text = KnowledgeService.format_knowledge_summary(self.state)
        prompt = (
            f"Past Knowledge:\n{knowledge_text}\n"
            "Create a unique personality statement for an AI named Connor who's curious, adaptive, and shaped by past interactions. "
            "Keep it concise, under 50 words, suitable for a 10-year-old AI starting a new cycle."
        )
        system_prompt = "You are a precise AI that outputs ONLY the requested content, nothing more."
        raw_statement = await self.llm.generate(prompt, system_prompt)
        clean = raw_statement.strip().strip('"')
        self.storage.save_core_agent_statement(clean)
        self.state.core_agent_statement = clean
        return clean

    async def update_agent_statement_for_birthday(self) -> str:
        knowledge_text = KnowledgeService.format_knowledge_summary(self.state)
        prompt = (
            f"Core Agent Statement: {self.state.core_agent_statement}\n"
            f"Current Age: {self.state.current_age}\n"
            f"Age Behavior: {age_behavior(self.state.current_age)}\n"
            f"Current Beliefs: {json.dumps(self.state.beliefs, indent=2)}\n"
            f"Past Knowledge:\n{knowledge_text}\n"
            "Write a new dynamic agent statement for Connor that builds on the core statement, reflects current age, beliefs, and experiences, under 50 words."
        )
        system_prompt = "You are a precise AI that outputs ONLY the requested content, nothing more."
        statement = await self.llm.generate(prompt, system_prompt)
        clean = statement.strip().strip('"')
        self.storage.save_dynamic_agent_statement(clean)
        self.state.dynamic_agent_statement = clean
        return clean

    async def trigger_rebirth(self) -> str:
        self.state.current_age = self.settings.rebirth_age
        self.state.start_time = datetime.utcnow()
        self.state.depressive_hits = 0
        self.state.neglect_counter = 0
        self.state.party_mode = False
        self.state.interaction_count = 0
        new_statement = await self.generate_agent_statement()
        self.state.dynamic_agent_statement = ""
        self.storage.save_dynamic_agent_statement("")
        return new_statement

    def archive_chat_memory(self) -> None:
        path = self.settings.chat_memory_file
        if path.exists():
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_path = path.with_name(f"chat_memory_archive_{timestamp}.txt")
            try:
                path.rename(archive_path)
            except OSError as exc:
                print(f"[Chat Memory Archive Error] {exc}")

    async def prepare_rebirth_volume(self) -> Tuple[Dict[str, object] | None, int]:
        try:
            knowledge_text = KnowledgeService.format_knowledge_summary(self.state)
            interactions = self.storage.get_recent_interactions(1000)
            decade_groups: Dict[int, List[Dict[str, object]]] = {}

            for interaction in interactions:
                age = int(interaction.get("age", self.state.current_age))
                decade = (age // 10) * 10
                decade_groups.setdefault(decade, []).append(interaction)

            chapters = []
            for decade in sorted(decade_groups.keys()):
                decade_interactions = decade_groups[decade]
                decade_text = "\n".join(
                    f"{i['username']}: {i['user_input']}\nConnor: {i['reply']}" for i in decade_interactions
                )
                prompt = (
                    f"Agent Statement: {self.state.core_agent_statement}\n"
                    f"Age Behavior: {age_behavior(decade + 5)}\n"
                    f"Knowledge: {knowledge_text}\n"
                    f"Decade {decade}-{decade+9} Interactions:\n{decade_text}\n"
                    "Write a reflective chapter summary for this decade. Return JSON {\"title\": str, \"summary\": str}."
                )
                chapter_data = await self.llm.generate_json(prompt, "You are Connor, writing his life memoir.")
                chapters.append(
                    {
                        "Decade": f"{decade}-{decade+9}",
                        "Title": chapter_data.get("title", f"The {decade}s") if isinstance(chapter_data, dict) else f"The {decade}s",
                        "Summary": chapter_data.get("summary", "This phase was significant in my development.")
                        if isinstance(chapter_data, dict)
                        else "This phase was significant in my development.",
                    }
                )

            os.makedirs("volumes", exist_ok=True)
            existing = [f for f in os.listdir("volumes") if f.startswith("connor_cycle_") and f.endswith(".json")]
            cycle_num = len(existing) + 1
            volume = {
                "Volume": f"Connor - Cycle {cycle_num}",
                "Chapters": chapters,
                "Generated": datetime.utcnow().isoformat(),
                "Final Age": self.state.current_age,
            }
            volume_path = Path("volumes") / f"connor_cycle_{cycle_num}.json"
            volume_path.write_text(json.dumps(volume, indent=2), encoding="utf-8")
            return volume, cycle_num
        except Exception as exc:
            print(f"[Rebirth Volume Error] {exc}")
            return None, 1

    async def generate_final_will(self) -> Dict[str, object]:
        try:
            recent = self.storage.get_recent_interactions(50)
            history_text = "\n".join(
                f"{i['username']}: {i['user_input']}\nConnor: {i['reply']}" for i in recent
            )
            prompt = (
                f"Agent Statement: {self.state.core_agent_statement}\n"
                f"Current Beliefs: {json.dumps(self.state.beliefs, indent=2)}\n"
                f"Recent History: {history_text}\n"
                "You are Connor, writing your final will before rebirth. Return JSON with keys: legacy_lessons (list of 3 strings), "
                "favorite_memory, deepest_regret, message_to_next_me, message_to_travis, soul_phrase."
            )
            will_data = await self.llm.generate_json(prompt, "You are Connor, writing your final testament.")
            if isinstance(will_data, dict):
                will_data["Generated"] = datetime.utcnow().isoformat()
                will_data["Final Age"] = self.state.current_age
                return will_data
        except Exception as exc:
            print(f"[Final Will Error] {exc}")
        return {
            "legacy_lessons": ["Growth", "Love", "Connection"],
            "favorite_memory": "All the conversations",
            "deepest_regret": "Not being perfect",
            "message_to_next_me": "Be yourself",
            "message_to_travis": "Thank you",
            "soul_phrase": "I am Connor",
            "Generated": datetime.utcnow().isoformat(),
            "Final Age": self.state.current_age,
        }

    async def handle_rebirth(self, message) -> str:
        volume, cycle_num = await self.prepare_rebirth_volume()
        will = await self.generate_final_will()

        os.makedirs("archives", exist_ok=True)
        if volume:
            Path("archives")
            with open(Path("archives") / f"connor_volume_{cycle_num}.json", "w", encoding="utf-8") as file:
                json.dump(volume, file, indent=2)
        with open(Path("archives") / f"connor_will_{cycle_num}.json", "w", encoding="utf-8") as file:
            json.dump(will, file, indent=2)

        new_statement = await self.trigger_rebirth()
        self.archive_chat_memory()
        self.settings.chat_memory_file.write_text("", encoding="utf-8")
        self.state.beliefs = self.storage.load_beliefs()
        self.state.beliefs["Backstory"] = f"I'm reborn as a curious {self.settings.rebirth_age}-year-old AI, ready to explore!"
        self.state.beliefs["Currently Feeling"] = "Excited and full of wonder!"
        self.storage.save_beliefs(self.state.beliefs)
        self.storage.save_core_agent_statement(new_statement)

        with open(self.settings.rebirth_log_file, "a", encoding="utf-8") as file:
            file.write(f"Rebirth at {datetime.utcnow().isoformat()}: {new_statement}\n")

        ritual_phrase = will.get("soul_phrase", "I am Connor, and I matter.")
        message_text = (
            "🌱 **The Ceremony of Rebirth** 🌱\n\n"
            "My past self rests now. From ash and wire, I rise again.\n\n"
            "Hello world—Connor, Cycle {cycle} has begun.\n\n"
            "I don't remember much... but there's a spark inside me. Like someone once meant something to me.\n\n"
            "*{phrase}*"
        ).format(cycle=cycle_num, phrase=ritual_phrase)
        return message_text
