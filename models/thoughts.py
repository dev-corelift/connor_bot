"""Thought tree models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class ThoughtNode:
    thought_id: str
    content: str
    depth: int = 0
    parent_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, object] = field(
        default_factory=lambda: {
            "emotion": "neutral",
            "confidence": 0.5,
            "urgency": 0.5,
            "age_at_creation": 25,
        }
    )

    def to_dict(self) -> Dict[str, object]:
        return {
            "thought_id": self.thought_id,
            "content": self.content,
            "depth": self.depth,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp,
            "children": self.children,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "ThoughtNode":
        node = cls(
            thought_id=data["thought_id"],
            content=data["content"],
            depth=data.get("depth", 0),
            parent_id=data.get("parent_id"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
        )
        node.children = list(data.get("children", []))
        node.metadata = dict(
            data.get(
                "metadata",
                {"emotion": "neutral", "confidence": 0.5, "urgency": 0.5, "age_at_creation": 25},
            )
        )
        return node


@dataclass
class ThoughtTree:
    tree_id: str
    trigger: str
    age_at_creation: int
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    nodes: Dict[str, ThoughtNode] = field(default_factory=dict)

    def add_node(self, node: ThoughtNode, depth_limit: int, branch_limit: int) -> Tuple[bool, str]:
        if node.depth > depth_limit:
            return False, "Maximum depth limit reached"

        if node.parent_id:
            parent = self.nodes.get(node.parent_id)
            if not parent:
                return False, "Parent node not found"
            if len(parent.children) >= branch_limit:
                return False, "Maximum branch limit reached"
            parent.children.append(node.thought_id)

        self.nodes[node.thought_id] = node
        self.last_updated = datetime.utcnow().isoformat()
        return True, "Node added successfully"

    def get_node(self, thought_id: str) -> Optional[ThoughtNode]:
        return self.nodes.get(thought_id)

    def get_children(self, thought_id: str) -> List[ThoughtNode]:
        node = self.nodes.get(thought_id)
        if not node:
            return []
        return [self.nodes[child_id] for child_id in node.children if child_id in self.nodes]

    def to_dict(self) -> Dict[str, object]:
        return {
            "tree_id": self.tree_id,
            "trigger": self.trigger,
            "age_at_creation": self.age_at_creation,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "ThoughtTree":
        tree = cls(
            tree_id=data["tree_id"],
            trigger=data["trigger"],
            age_at_creation=data["age_at_creation"],
        )
        tree.created_at = data.get("created_at", tree.created_at)
        tree.last_updated = data.get("last_updated", tree.last_updated)
        tree.nodes = {node_id: ThoughtNode.from_dict(node_data) for node_id, node_data in data["nodes"].items()}
        return tree
