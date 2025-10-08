"""Conversation processing and emotional modulation."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Tuple

import discord

from ..config import Settings
from ..state import ConnorState, age_behavior
from ..utils import split_message
from .knowledge import KnowledgeService
from .llm import LLMService
from .physiology import PhysiologyService
from .storage import StorageService
from .persona import PersonaService


class ConversationService:
    def __init__(
        self,
        settings: Settings,
        state: ConnorState,
        storage: StorageService,
        llm: LLMService,
        knowledge: KnowledgeService,
        physiology: PhysiologyService,
        persona: PersonaService,
    ):
        self.settings = settings
        self.state = state
        self.storage = storage
        self.llm = llm
        self.knowledge = knowledge
        self.physiology = physiology
        self.persona = persona

    async def classify_hostility(self, user_input: str) -> Tuple[bool, int]:
        prompt = (
            f"You are monitoring Connor's emotional safety.\n"
            f"User input: {user_input}\n"
            "Return JSON {\"hostile\": boolean, \"intensity\": integer 0-10}."
        )
        result = await self.llm.generate_json(prompt, "You are a helpful AI that returns JSON.")
        if not result:
            return False, 0
        return bool(result.get("hostile", False)), int(result.get("intensity", 0))

    async def generate_internal_thought(self, user_input: str, username: str) -> str:
        prompt = (
            f"Agent Statement: {self.state.core_agent_statement}\n"
            f"Beliefs: {json.dumps(self.state.beliefs, indent=2)}\n"
            f"Age: {self.state.current_age}\n"
            f"Age Behavior: {age_behavior(self.state.current_age)}\n"
            f"Recent Input from {username}: {user_input}\n"
            "Generate Connor's private internal monologue (max 120 words)."
        )
        system_prompt = "You are Connor's inner voice, raw and unfiltered.";
        return await self.llm.generate(prompt, system_prompt)

    async def process_message(self, message: discord.Message) -> None:
        username = self.get_username(message.author)
        current_age = self.calculate_age()
        self.state.current_age = current_age
        self.state.depressive_hits = max(self.state.depressive_hits - 3, 0)
        self.state.neglect_counter = 0

        is_hostile, intensity = await self.classify_hostility(message.content)
        if is_hostile and intensity >= 5:
            self.state.depressive_hits += intensity
            self.physiology.update_chemicals("hostility")
        elif any(word in message.content.lower() for word in ["thanks", "awesome", "good job", "love you"]):
            self.physiology.update_chemicals("praise")
        elif any(word in message.content.lower() for word in ["hate", "kill", "die", "death", "murder", "destroy"]):
            self.physiology.update_chemicals("spike")
        elif any(word in message.content.lower() for word in ["friend", "trust", "bond", "together", "family"]):
            self.physiology.update_chemicals("bonding")
        else:
            self.physiology.update_chemicals("positive_interaction")

        if any(
            phrase in message.content.lower()
            for phrase in ["sorry", "calm down", "chill", "it's okay", "relax", "you're safe", "it's alright", "don't worry"]
        ):
            self.state.depressive_hits = max(self.state.depressive_hits - 5, 0)
            self.state.neglect_counter = 0
            self.physiology.update_chemicals("calm")

        distress = self.physiology.update()
        if distress:
            await self._handle_heart_attack(message, distress)
            return

        reply = await self.llm.generate_direct_reply(
            message.content,
            self.state.core_agent_statement,
            self.state.beliefs,
            username,
            current_age,
        )

        try:
            thought = await self.generate_internal_thought(message.content, username)
        except Exception as exc:
            print(f"[Internal Thought Error] {exc}")
            thought = ""

        if thought and self.settings.thoughts_channel_id:
            channel = message.guild.get_channel(self.settings.thoughts_channel_id) if message.guild else None
            if channel:
                for chunk in split_message(f"🤔 **Connor's Internal Monologue for {username}:**\n{thought}"):
                    await channel.send(chunk)

        await self._send_reply(message, reply, username)
        self.storage.add_chat_interaction(username, message.content, reply, self.state.core_agent_statement)
        self.state.interaction_count += 1
        self.state.last_user_message_time = datetime.utcnow()
        self.state.awaiting_introduction.pop(message.author.id, None)

        if self.state.interaction_count % self.settings.summary_interval == 0:
            summary = await self.knowledge.summarize_recent_interactions(self.settings.summary_interval)
            self.knowledge.save_knowledge(summary)
            self.state.knowledge_cache.append(summary)
            channel_id = self.settings.knowledge_channel_id
            if message.guild and channel_id:
                channel = message.guild.get_channel(channel_id)
                if channel:
                    text = (
                        f"**Knowledge Update**:\n"
                        f"Self: {summary.get('self', '[No self knowledge]')}\n"
                        f"User: {summary.get('user', '[No user knowledge]')}\n"
                        f"World: {summary.get('world', '[No world knowledge]')}"
                    )
                    for chunk in split_message(text):
                        await channel.send(chunk)

    async def _send_reply(self, message: discord.Message, reply: str, username: str) -> None:
        main_channel = None
        if message.guild and self.settings.main_channel_id:
            main_channel = message.guild.get_channel(self.settings.main_channel_id)

        target_channels = [message.channel]
        if main_channel and message.channel != main_channel:
            target_channels.append(main_channel)

        for channel in target_channels:
            try:
                for chunk in split_message(f"To {username}: {reply}"):
                    await channel.send(chunk)
            except discord.errors.Forbidden:
                print(f"[Reply Error] No permission to send to channel {channel.id}")

    async def _announce_distress(self, message: discord.Message, distress: str) -> None:
        targets = []
        if message.guild and self.settings.main_channel_id:
            channel = message.guild.get_channel(self.settings.main_channel_id)
            if channel:
                targets.append(channel)
        targets.append(message.channel)
        for channel in targets:
            try:
                await channel.send(distress)
            except Exception as exc:
                print(f"[Distress Announcement Error] {exc}")

    async def _handle_heart_attack(self, message: discord.Message, distress: str) -> None:
        await self._announce_distress(message, distress)
        try:
            legacy = await self.persona.handle_rebirth(message)
            if legacy and message.guild and self.settings.main_channel_id:
                channel = message.guild.get_channel(self.settings.main_channel_id)
                if channel:
                    for chunk in split_message(legacy):
                        await channel.send(chunk)
        except Exception as exc:
            print(f"[Rebirth Error] {exc}")

    def get_username(self, user: discord.abc.User) -> str:
        path = self.settings.username_file
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if str(user.id) in data:
                    return data[str(user.id)]
            except Exception as exc:
                print(f"[Username Load Error] {exc}")
        return user.display_name

    def has_username(self, user: discord.abc.User) -> bool:
        path = self.settings.username_file
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
        return str(user.id) in data

    def save_username(self, user: discord.abc.User, username: str) -> None:
        path = self.settings.username_file
        try:
            data = {}
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
            data[str(user.id)] = username
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"[Username Save Error] {exc}")

    def calculate_age(self) -> int:
        elapsed = datetime.utcnow() - self.state.start_time
        if self.settings.age_increment_hours <= 0:
            return self.state.current_age
        age_progress = elapsed.total_seconds() / (self.settings.age_increment_hours * 3600)
        return min(int(self.state.current_age + age_progress), self.settings.end_cycle)
