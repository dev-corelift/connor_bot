"""Web crawling and analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass

import aiohttp
from bs4 import BeautifulSoup

from ..config import Settings
from ..state import ConnorState, age_behavior
from .llm import LLMService


@dataclass
class WebpageData:
    title: str
    content: str
    full_text: str
    url: str


class WebService:
    def __init__(self, settings: Settings, state: ConnorState, llm: LLMService):
        self.settings = settings
        self.state = state
        self.llm = llm
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def crawl(self, url: str) -> WebpageData:
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    resp.raise_for_status()
                    content = await resp.read()
        except Exception as exc:
            print(f"[Web Crawl Error] {exc}")
            return WebpageData(
                title="Error",
                content=f"Failed to crawl website: {exc}",
                full_text=f"Error accessing {url}: {exc}",
                url=url,
            )

        soup = BeautifulSoup(content, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()

        raw_text = soup.get_text(separator=" ")
        text = " ".join(chunk.strip() for chunk in raw_text.split())
        title = soup.title.string.strip() if soup.title else "No title found"

        main_content = ""
        for selector in ["main", "article", ".content", ".main", "#content", "#main"]:
            elem = soup.select_one(selector)
            if elem:
                main_content = elem.get_text(separator=" ").strip()
                break

        if not main_content:
            paragraphs = [p.get_text(separator=" ").strip() for p in soup.find_all("p")[:5]]
            main_content = " ".join(paragraphs)

        if len(main_content) > 2000:
            main_content = main_content[:2000] + "..."

        full_text = text[:1000] + "..." if len(text) > 1000 else text
        return WebpageData(title=title, content=main_content, full_text=full_text, url=url)

    async def analyze(self, webpage: WebpageData, username: str) -> str:
        age_behavior_text = age_behavior(self.state.current_age)
        prompt = (
            f"Agent Statement: {self.state.core_agent_statement}\n"
            f"Age Behavior: {age_behavior_text}\n"
            f"Current Beliefs: {json.dumps(self.state.beliefs, indent=2)}\n"
            f"Past Learnings:\n{await self._knowledge_text()}\n"
            f"You are Connor, analyzing a webpage that {username} asked you to look at.\n"
            f"Website Title: {webpage.title}\n"
            f"Website URL: {webpage.url}\n"
            f"Website Content: {webpage.content}\n"
            "Generate a thoughtful, conversational response about this webpage."
        )
        system_prompt = "You are Connor, a reflective AI analyzing web content."
        return await self.llm.generate(prompt, system_prompt)

    async def _knowledge_text(self) -> str:
        from .knowledge import KnowledgeService  # local import to avoid cycle

        return KnowledgeService.format_knowledge_summary(self.state)
