"""Thought tree generation and expansion."""

from __future__ import annotations

import json
import uuid
from typing import Dict, Tuple

from ..config import Settings
from ..models.thoughts import ThoughtNode, ThoughtTree
from ..state import ConnorState, age_behavior
from .knowledge import KnowledgeService
from .llm import LLMService
from .storage import StorageService


class ThoughtService:
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
        self.depth_limit = 10
        self.branch_limit = 8
        self.expansion_limit = 5

    def load_trees(self) -> Dict[str, ThoughtTree]:
        return self.storage.load_thought_trees(ThoughtTree.from_dict)

    def save_trees(self, trees: Dict[str, ThoughtTree]) -> None:
        self.storage.save_thought_trees(trees)

    async def generate_tree(self, trigger: str) -> Tuple[ThoughtTree | None, str]:
        tree_id = str(uuid.uuid4())
        tree = ThoughtTree(tree_id, trigger, self.state.current_age)
        success, msg = await self._add_generated_nodes(tree, None, trigger)
        if not success:
            return None, msg
        trees = self.load_trees()
        trees[tree.tree_id] = tree
        self.save_trees(trees)
        return tree, f"Started thought tree `{tree.tree_id}`"

    async def expand_tree(self, tree_id: str, thought_id: str) -> Tuple[list[ThoughtNode], str]:
        trees = self.load_trees()
        tree = trees.get(tree_id)
        if not tree:
            return [], "Thought tree not found"

        parent = tree.get_node(thought_id)
        if not parent:
            return [], "Thought not found"

        success, msg = await self._add_generated_nodes(tree, parent, parent.content)
        if not success:
            return [], msg

        self.save_trees(trees)
        return [tree.get_node(child_id) for child_id in parent.children], "Thought expanded"

    def recent_trees(self, limit: int = 5) -> list[ThoughtTree]:
        trees = self.load_trees()
        sorted_trees = sorted(trees.values(), key=lambda t: t.last_updated, reverse=True)
        return sorted_trees[:limit]

    async def auto_think(self, trigger: str) -> str:
        tree, message = await self.generate_tree(trigger)
        if tree:
            return f"Started auto thought tree `{tree.tree_id}`"
        return message

    async def massive_brainstorm(self, trigger: str, branches: int = 3) -> ThoughtTree | None:
        tree, message = await self.generate_tree(trigger)
        if not tree:
            print(f"[Massive Brainstorm] Failed: {message}")
            return None

        for node in list(tree.nodes.values()):
            for _ in range(branches):
                await self._add_generated_nodes(tree, node, node.content)

        trees = self.load_trees()
        trees[tree.tree_id] = tree
        self.save_trees(trees)
        return tree

    async def _add_generated_nodes(
        self,
        tree: ThoughtTree,
        parent: ThoughtNode | None,
        trigger_text: str,
    ) -> Tuple[bool, str]:
        knowledge = self.knowledge.get_knowledge()
        knowledge_text = KnowledgeService.format_knowledge_summary(self.state)
        age_behavior_text = age_behavior(self.state.current_age)

        prompt = (
            f"Agent Statement: {self.state.core_agent_statement}\n"
            f"Age Behavior: {age_behavior_text}\n"
            f"Beliefs: {json.dumps(self.state.beliefs, indent=2)}\n"
            f"Past Learnings:\n{knowledge_text}\n"
            f"Trigger Thought: {trigger_text}\n"
            "Generate up to {limit} multi-branch thoughts. Return JSON list with fields"
            " 'content', 'emotion', 'urgency', 'confidence'."
        ).format(limit=self.expansion_limit)
        system_prompt = "You are Connor's mind expanding complex thought branches."
        response = await self.llm.generate_json(prompt, system_prompt)

        if not isinstance(response, list):
            return False, "Failed to generate thoughts"

        added_nodes = []
        for item in response:
            thought_id = str(uuid.uuid4())
            node = ThoughtNode(
                thought_id=thought_id,
                content=item.get("content", ""),
                depth=(parent.depth + 1) if parent else 0,
                parent_id=parent.thought_id if parent else None,
            )
            node.metadata.update(
                {
                    "emotion": item.get("emotion", "neutral"),
                    "confidence": float(item.get("confidence", 0.5)),
                    "urgency": float(item.get("urgency", 0.5)),
                    "age_at_creation": self.state.current_age,
                }
            )
            ok, msg = tree.add_node(node, self.depth_limit, self.branch_limit)
            if not ok:
                return False, msg
            added_nodes.append(node)
        return True, "Added thoughts"

    def format_tree(self, tree: ThoughtTree, max_depth: int = 5) -> str:
        lines = [f"🌳 Thought Tree: {tree.trigger} (Age {tree.age_at_creation})"]

        def walk(node: ThoughtNode, depth: int) -> None:
            if depth > max_depth:
                return
            indent = "  " * depth
            lines.append(f"{indent}- {node.content}")
            for child_id in node.children:
                child = tree.get_node(child_id)
                if child:
                    walk(child, depth + 1)

        roots = [node for node in tree.nodes.values() if not node.parent_id]
        for root in roots:
            walk(root, 0)

        return "\n".join(lines)

    def tree_summary(self, tree: ThoughtTree) -> str:
        return f"Tree `{tree.tree_id}` about {tree.trigger} with {len(tree.nodes)} thoughts"
