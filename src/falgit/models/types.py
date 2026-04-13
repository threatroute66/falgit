"""Core data types for falgit."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum


def node_key(labels: list[str], props: dict) -> str:
    """Generate a content-based identity key for a node."""
    canonical = json.dumps(
        {"l": sorted(labels), "p": sorted(props.items())},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def edge_key(rel_type: str, src_key: str, dst_key: str, props: dict) -> str:
    """Generate a content-based identity key for an edge."""
    canonical = json.dumps(
        {"t": rel_type, "s": src_key, "d": dst_key, "p": sorted(props.items())},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class NodeState:
    """Represents the state of a single graph node."""

    labels: tuple[str, ...]
    props: dict
    key: str = ""

    def __post_init__(self):
        if not self.key:
            object.__setattr__(self, "key", node_key(list(self.labels), self.props))

    def to_dict(self) -> dict:
        return {"labels": list(self.labels), "props": self.props, "key": self.key}

    @classmethod
    def from_dict(cls, d: dict) -> NodeState:
        return cls(labels=tuple(d["labels"]), props=d["props"], key=d.get("key", ""))


@dataclass(frozen=True)
class EdgeState:
    """Represents the state of a single graph edge."""

    rel_type: str
    src_key: str
    dst_key: str
    props: dict
    key: str = ""

    def __post_init__(self):
        if not self.key:
            computed = edge_key(self.rel_type, self.src_key, self.dst_key, self.props)
            object.__setattr__(self, "key", computed)

    def to_dict(self) -> dict:
        return {
            "rel_type": self.rel_type,
            "src_key": self.src_key,
            "dst_key": self.dst_key,
            "props": self.props,
            "key": self.key,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EdgeState:
        return cls(
            rel_type=d["rel_type"],
            src_key=d["src_key"],
            dst_key=d["dst_key"],
            props=d["props"],
            key=d.get("key", ""),
        )


@dataclass
class GraphSnapshot:
    """Complete snapshot of a graph's state."""

    nodes: dict[str, NodeState] = field(default_factory=dict)
    edges: dict[str, EdgeState] = field(default_factory=dict)

    def to_json(self) -> tuple[str, str]:
        """Serialize to JSON strings for storage."""
        nodes_json = json.dumps(
            [n.to_dict() for n in self.nodes.values()], default=str
        )
        edges_json = json.dumps(
            [e.to_dict() for e in self.edges.values()], default=str
        )
        return nodes_json, edges_json

    @classmethod
    def from_json(cls, nodes_json: str, edges_json: str) -> GraphSnapshot:
        """Deserialize from JSON strings."""
        nodes = {}
        for d in json.loads(nodes_json):
            ns = NodeState.from_dict(d)
            nodes[ns.key] = ns
        edges = {}
        for d in json.loads(edges_json):
            es = EdgeState.from_dict(d)
            edges[es.key] = es
        return cls(nodes=nodes, edges=edges)

    @classmethod
    def empty(cls) -> GraphSnapshot:
        return cls()


class OpType(str, Enum):
    ADD_NODE = "ADD_NODE"
    DEL_NODE = "DEL_NODE"
    MOD_NODE = "MOD_NODE"
    ADD_EDGE = "ADD_EDGE"
    DEL_EDGE = "DEL_EDGE"
    MOD_EDGE = "MOD_EDGE"


@dataclass
class DiffOp:
    """A single change operation between two graph states."""

    op: OpType
    element_key: str
    data: dict | None = None
    old_data: dict | None = None

    def to_dict(self) -> dict:
        return {
            "op": self.op.value,
            "element_key": self.element_key,
            "data": self.data,
            "old_data": self.old_data,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DiffOp:
        return cls(
            op=OpType(d["op"]),
            element_key=d["element_key"],
            data=d.get("data"),
            old_data=d.get("old_data"),
        )


@dataclass
class Commit:
    """A falgit commit."""

    commit_id: str
    message: str
    timestamp: int
    parent_id: str | None
    has_snapshot: bool
    branch: str

    def to_dict(self) -> dict:
        return {
            "commit_id": self.commit_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "has_snapshot": self.has_snapshot,
            "branch": self.branch,
        }


@dataclass
class Branch:
    """A falgit branch."""

    name: str
    head_commit_id: str | None
    is_active: bool


@dataclass
class Status:
    """Summary of changes since the last commit."""

    added_nodes: list[str] = field(default_factory=list)
    deleted_nodes: list[str] = field(default_factory=list)
    modified_nodes: list[str] = field(default_factory=list)
    added_edges: list[str] = field(default_factory=list)
    deleted_edges: list[str] = field(default_factory=list)
    modified_edges: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not any([
            self.added_nodes,
            self.deleted_nodes,
            self.modified_nodes,
            self.added_edges,
            self.deleted_edges,
            self.modified_edges,
        ])

    @property
    def total_changes(self) -> int:
        return (
            len(self.added_nodes)
            + len(self.deleted_nodes)
            + len(self.modified_nodes)
            + len(self.added_edges)
            + len(self.deleted_edges)
            + len(self.modified_edges)
        )


@dataclass
class MergeResult:
    """Result of a merge operation."""

    commit: Commit
    auto_resolved: int
    source_branch: str
    target_branch: str
