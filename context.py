"""Shared context for Connor bot."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .services.conversation import ConversationService
from .services.llm import LLMService
from .services.knowledge import KnowledgeService
from .services.persona import PersonaService
from .services.physiology import PhysiologyService
from .services.reflection import ReflectionService
from .services.speech import SpeechService
from .services.storage import StorageService
from .services.thought import ThoughtService
from .services.voice import VoiceService
from .services.web import WebService
from .state import ConnorState


@dataclass
class ConnorContext:
    settings: Settings
    state: ConnorState
    storage: StorageService
    llm: LLMService
    voice: VoiceService
    knowledge: KnowledgeService
    thought: ThoughtService
    physiology: PhysiologyService
    conversation: ConversationService
    web: WebService
    persona: PersonaService
    reflection: ReflectionService
    speech: SpeechService


def build_context(settings: Settings) -> ConnorContext:
    state = ConnorState(current_age=settings.initial_age)
    storage = StorageService(settings, state)
    openai_client = None
    try:
        if settings.openai_api_key:
            from openai import OpenAI

            openai_client = OpenAI(api_key=settings.openai_api_key)
    except Exception as exc:
        print(f"[OpenAI Init Error] {exc}")

    llm = LLMService(settings, state, openai_client=openai_client)
    voice = VoiceService(settings)
    knowledge = KnowledgeService(settings, state, storage, llm)
    physiology = PhysiologyService(state)
    thought = ThoughtService(settings, state, storage, knowledge, llm)
    persona = PersonaService(settings, state, storage, knowledge, llm)
    reflection = ReflectionService(settings, state, storage, knowledge, llm)
    speech = SpeechService(settings.whisper_model)
    conversation = ConversationService(settings, state, storage, llm, knowledge, physiology, persona)
    web = WebService(settings, state, llm)

    state.core_agent_statement = storage.load_core_agent_statement()
    state.dynamic_agent_statement = storage.load_dynamic_agent_statement()
    state.beliefs = storage.load_beliefs()
    state.model = settings.ollama_model
    state.backend = "ollama"
    state.start_time = state.start_time
    state.knowledge_cache = knowledge.get_knowledge()

    return ConnorContext(
        settings=settings,
        state=state,
        storage=storage,
        llm=llm,
        voice=voice,
        knowledge=knowledge,
        thought=thought,
        physiology=physiology,
        conversation=conversation,
        web=web,
        persona=persona,
        reflection=reflection,
        speech=speech,
    )
