"""Knowledge summarization and storage."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from ..config import Settings
from ..state import ConnorState, age_behavior
from ..utils import split_message
from .llm import LLMService
from .storage import StorageService


class KnowledgeService:
    def __init__(self, settings: Settings, state: ConnorState, storage: StorageService, llm: LLMService):
        self.settings = settings
        self.state = state
        self.storage = storage
        self.llm = llm

    async def summarize_recent_interactions(self, limit: int) -> Dict[str, Any]:
        interactions = self.storage.get_recent_interactions(limit)
        history = "\n".join(
            [f"{i['username']}: {i['user_input']}\nReply: {i['reply']}" for i in interactions]
        )
        prompt = (
            f"Agent Statement: {self.state.core_agent_statement}\n"
            f"You've had the following interactions with {self.state.current_age}-year-old Connor:\n"
            f"{history}\n"
            "Summarize key learnings. Return JSON with keys 'self', 'user', 'world'."
        )
        system_prompt = "You are a helpful AI assistant that returns strict JSON."
        result = await self.llm.generate_json(prompt, system_prompt)
        if not result:
            return {
                "self": "[Invalid JSON response for self knowledge]",
                "user": "[Invalid JSON response for user knowledge]",
                "world": "[Invalid JSON response for world knowledge]",
            }
        return result

    def save_knowledge(self, summary: Dict[str, Any]) -> None:
        path = self.settings.knowledge_file
        timestamp = datetime.utcnow().isoformat()
        try:
            existing: List[str] = []
            if path.exists():
                existing = path.read_text(encoding="utf-8").splitlines()
            entry = f"[{timestamp}] {json.dumps(summary)}"
            existing.append(entry)
            existing = existing[-10:]
            path.write_text("\n".join(existing) + "\n", encoding="utf-8")
        except Exception as exc:
            print(f"[Knowledge Save Error] {exc}")

    def get_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        path = self.settings.knowledge_file
        if not path.exists():
            return []
        knowledge: List[Dict[str, Any]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in lines[-limit:]:
                if "[" in line and "]" in line:
                    json_part = line.split("]", 1)[-1].strip()
                    try:
                        knowledge.append(json.loads(json_part))
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            print(f"[Knowledge Load Error] {exc}")
        return knowledge

    async def update_beliefs(self, username: str) -> Dict[str, Any]:
        interactions = self.storage.get_recent_interactions(self.settings.recent_history_limit)
        history = "\n".join([f"{i['username']}: {i['user_input']}\nReply: {i['reply']}" for i in interactions])
        knowledge_text = KnowledgeService.format_knowledge_summary(self.state)
        prompt = (
            f"Agent Statement: {self.state.core_agent_statement}\n"
            f"Age Behavior: {age_behavior(self.state.current_age)}\n"
            f"Previous Beliefs: {json.dumps(self.state.beliefs, indent=2)}\n"
            f"Past Learnings:\n{knowledge_text}\n"
            f"Recent Interactions with {username}:\n{history}\n"
            "Update the beliefs to reflect the current maturity and specific reflections. "
            "Return the full belief set in JSON format."
        )
        result = await self.llm.generate_json(prompt, "You are a helpful AI assistant that returns JSON.")
        if isinstance(result, dict) and result:
            return result
        return self.state.beliefs

    async def birthday_message(self, username: str) -> str:
        knowledge_text = KnowledgeService.format_knowledge_summary(self.state)
        prompt = (
            f"Agent Statement: {self.state.core_agent_statement}\n"
            f"Age Behavior: {age_behavior(self.state.current_age)}\n"
            f"Current Beliefs: {json.dumps(self.state.beliefs, indent=2)}\n"
            f"Past Learnings:\n{knowledge_text}\n"
            f"You are Connor, talking to {username}. You've just reached a new level of maturity (age {self.state.current_age}). "
            "Generate a reflective message about your growth in no more than 25 words."
        )
        return await self.llm.generate(prompt, "You are Connor, a reflective AI.")

    @staticmethod
    def format_knowledge_summary(state: ConnorState) -> str:
        knowledge = getattr(state, "knowledge_cache", [])
        if not knowledge:
            return "No prior knowledge available."
        lines = []
        for item in knowledge:
            lines.append(f"- Self: {item.get('self', 'N/A')}")
            lines.append(f"  User: {item.get('user', 'N/A')}")
            lines.append(f"  World: {item.get('world', 'N/A')}")
        return "\n".join(lines)
