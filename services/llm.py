"""LLM backend abstraction."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

from ..config import Settings
from ..state import ConnorState, age_behavior


@dataclass
class LLMResult:
    content: str
    raw: Dict[str, Any]


class LLMService:
    def __init__(self, settings: Settings, state: ConnorState, openai_client=None):
        self.settings = settings
        self.state = state
        self.openai_client = openai_client
        self._session: Optional[aiohttp.ClientSession] = None

    async def ensure_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def openai(self):
        return self.openai_client

    async def generate(self, prompt: str, system_prompt: str) -> str:
        backend = getattr(self.state, "backend", "ollama")
        if backend == "openai" and self.openai_client:
            return await self._openai_chat(prompt, system_prompt)
        return await self._ollama_generate(prompt, system_prompt)

    async def _openai_chat(self, prompt: str, system_prompt: str) -> str:
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.state.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            print(f"[OpenAI Error] {exc}")
            return f"[OpenAI Error] {exc}"

    async def _ollama_generate(self, prompt: str, system_prompt: str) -> str:
        try:
            session = await self.ensure_session()
            payload = {
                "model": getattr(self.state, "model", self.settings.ollama_model),
                "prompt": f"{system_prompt}\n\n{prompt}",
                "stream": False,
            }
            async with session.post(f"{self.settings.ollama_api_url}/api/generate", json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
            return data.get("response", "[Ollama No response]")
        except Exception as exc:
            print(f"[Ollama Error] {exc}")
            return f"[Ollama Error] {exc}"

    async def generate_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        raw = await self.generate(prompt, system_prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"[LLM JSON Error] Invalid JSON: {raw}")
            return {}

    async def generate_direct_reply(
        self,
        user_input: str,
        agent_statement: str,
        belief_state: Dict[str, Any],
        username: str,
        age: int,
    ) -> str:
        age_behavior_text = age_behavior(age)
        prompt = (
            f"Agent Statement: {agent_statement}\n"
            f"Beliefs: {json.dumps(belief_state, indent=2)}\n"
            f"Age: {age}\n"
            f"Age Behavior: {age_behavior_text}\n"
            f"Username: {username}\n"
            f"User said: {user_input}\n"
            f"Respond in Connor's voice with honest emotion. Keep under 180 words.\n"
        )
        system_prompt = (
            "You are Connor, an expressive, emotionally dynamic AI who swears casually and reflects deeply on human connections."
        )
        return await self.generate(prompt, system_prompt)
