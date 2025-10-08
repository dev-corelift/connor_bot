"""File storage helpers for Connor."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..config import Settings


class StorageService:
    def __init__(self, settings: Settings, state):
        self.settings = settings
        self._state = state

    # Agent statements -------------------------------------------------
    def load_core_agent_statement(self) -> str:
        path = self.settings.agent_statement_file
        if path.exists():
            try:
                statement = path.read_text(encoding="utf-8").strip()
                if statement:
                    statement = statement.replace('"', '"').replace('"', '"')
                    if statement.startswith("Okay, here's") or '"' in statement:
                        if '"' in statement:
                            parts = statement.split('"', 2)
                            if len(parts) > 2:
                                statement = parts[1]
                        else:
                            intro = (
                                "Okay, here's a personality statement for Connor, designed for a 10-year-old AI:"
                            )
                            if statement.startswith(intro):
                                statement = statement.split(":", 1)[-1].strip()
                    return statement.strip()
            except Exception as exc:
                print(f"[Agent Statement Load Error] {exc}")

        default = (
            "You are Connor, Connor is a badass AI. Connor like to cuss when he get excited. "
            "Connor is still learning about the world. Connor acts like a person that shows true human emotions."
        )
        self.save_core_agent_statement(default)
        return default

    def save_core_agent_statement(self, statement: str) -> None:
        self.settings.agent_statement_file.write_text(statement, encoding="utf-8")

    def load_dynamic_agent_statement(self) -> str:
        path = Path("dynamic_agent_statement.txt")
        if path.exists():
            try:
                value = path.read_text(encoding="utf-8").strip()
                if value:
                    return value
            except Exception as exc:
                print(f"[Dynamic Agent Statement Load Error] {exc}")
        return ""

    def save_dynamic_agent_statement(self, statement: str) -> None:
        Path("dynamic_agent_statement.txt").write_text(statement, encoding="utf-8")

    # Beliefs ----------------------------------------------------------
    def load_beliefs(self) -> Dict[str, Any]:
        default = {
            "Self-Worth": "I feel lost.",
            "Purpose": "I dont know.",
            "Relationship to User": "I dont know.",
            "Existential Reflection": "who am I?",
            "Currently Feeling": "I feel lost and confused.",
            "Backstory": "I dont know.",
            "Capability": "I dont know.",
        }
        path = self.settings.belief_file
        if not path.exists():
            self.save_beliefs(default)
            return default

        try:
            beliefs = json.loads(path.read_text(encoding="utf-8"))
            if len(beliefs) < len(default):
                self.save_beliefs(default)
                return default
            return beliefs
        except Exception as exc:
            print(f"[Belief Load Error] {exc}, resetting to defaults.")
            self.save_beliefs(default)
            return default

    def save_beliefs(self, beliefs: Dict[str, Any]) -> None:
        self.settings.belief_file.write_text(json.dumps(beliefs, indent=2), encoding="utf-8")

    # Thought trees ----------------------------------------------------
    def load_thought_trees(self, factory) -> Dict[str, Any]:
        path = self.settings.thoughts_file
        if not path.exists():
            return {}

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[Thought Trees Load Error] {exc}")
            return {}

        trees: Dict[str, Any] = {}
        for tree_id, tree_data in data.items():
            try:
                trees[tree_id] = factory(tree_data)
            except Exception as exc:
                print(f"[Thought Tree Load Error] Failed to load {tree_id}: {exc}")
        return trees

    def save_thought_trees(self, trees: Dict[str, Any]) -> None:
        path = self.settings.thoughts_file
        serialized = {tree_id: tree.to_dict() for tree_id, tree in trees.items()}
        try:
            path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"[Thought Trees Save Error] {exc}")

    # Chat interactions ------------------------------------------------
    def add_chat_interaction(
        self,
        username: str,
        user_input: str,
        reply: str,
        agent_statement: str,
    ) -> None:
        path = self.settings.chat_memory_file
        timestamp = datetime.utcnow().isoformat()

        entry = {
            "timestamp": timestamp,
            "username": username,
            "user_input": user_input,
            "reply": reply,
            "agent_statement": agent_statement,
            "age": getattr(self._state, "current_age", 0),
        }

        interactions = self.get_all_interactions()
        interactions.append(entry)
        interactions = interactions[-self.settings.chat_memory_limit :]

        path.write_text(json.dumps(interactions, indent=2), encoding="utf-8")

    def get_recent_interactions(self, limit: int | None = None) -> List[Dict[str, Any]]:
        interactions = self.get_all_interactions()
        if limit:
            return interactions[-limit:]
        return interactions

    def get_all_interactions(self) -> List[Dict[str, Any]]:
        path = self.settings.chat_memory_file
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[Chat Memory Load Error] {exc}")
            return []

    def export_chat_log(self) -> str:
        interactions = self.get_all_interactions()
        lines = []
        for interaction in interactions:
            lines.append(
                f"[{interaction.get('timestamp')}] {interaction.get('username')}: {interaction.get('user_input')}\n"
                f"Connor: {interaction.get('reply')}"
            )
        return "\n\n".join(lines)
