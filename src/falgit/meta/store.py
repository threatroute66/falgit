"""MetadataStore — persistence layer for falgit metadata in FalkorDB."""

from __future__ import annotations

import json

from falgit.errors import BranchNotFoundError, CommitNotFoundError
from falgit.meta import schema
from falgit.models.types import (
    Branch,
    Commit,
    DiffOp,
    GraphSnapshot,
    OpType,
)


class MetadataStore:
    """Reads and writes falgit metadata to the _falgit_{name} graph."""

    def __init__(self, db, graph_name: str):
        self._db = db
        self._graph_name = graph_name
        self._meta_graph_name = f"_falgit_{graph_name}"
        self._meta_graph = db.select_graph(self._meta_graph_name)

    @property
    def meta_graph_name(self) -> str:
        return self._meta_graph_name

    def is_initialized(self) -> bool:
        """Check if the metadata graph exists and has a FalgitMeta node."""
        try:
            graphs = self._db.list_graphs()
            if self._meta_graph_name not in graphs:
                return False
            result = self._meta_graph.ro_query(
                schema.CHECK_INIT,
                params={"graph_name": self._graph_name},
            )
            return len(result.result_set) > 0
        except Exception:
            return False

    def initialize(self, timestamp: int) -> None:
        """Create the metadata graph with initial structures."""
        self._meta_graph.query(
            schema.INIT_META,
            params={"graph_name": self._graph_name, "created_at": timestamp},
        )
        self._meta_graph.query(
            schema.INIT_BRANCH,
            params={"name": "main", "is_active": True},
        )

    def save_commit(
        self,
        commit: Commit,
        snapshot: GraphSnapshot | None,
        diff_ops: list[DiffOp],
    ) -> None:
        """Persist a commit with optional snapshot and diff entries."""
        # Create commit node
        self._meta_graph.query(
            schema.CREATE_COMMIT,
            params={
                "commit_id": commit.commit_id,
                "message": commit.message,
                "timestamp": commit.timestamp,
                "has_snapshot": commit.has_snapshot,
                "branch": commit.branch,
            },
        )

        # Link to parent
        if commit.parent_id:
            self._meta_graph.query(
                schema.LINK_COMMIT_PARENT,
                params={"child_id": commit.commit_id, "parent_id": commit.parent_id},
            )

        # Update branch head
        self._meta_graph.query(
            schema.UPDATE_BRANCH_HEAD,
            params={"branch_name": commit.branch, "commit_id": commit.commit_id},
        )

        # Save snapshot if present
        if snapshot is not None:
            nodes_json, edges_json = snapshot.to_json()
            self._meta_graph.query(
                schema.CREATE_SNAPSHOT,
                params={
                    "commit_id": commit.commit_id,
                    "nodes_json": nodes_json,
                    "edges_json": edges_json,
                },
            )

        # Save diff entries
        for op in diff_ops:
            self._meta_graph.query(
                schema.CREATE_DIFF_ENTRY,
                params={
                    "commit_id": commit.commit_id,
                    "op": op.op.value,
                    "element_key": op.element_key,
                    "data_json": json.dumps(op.data, default=str) if op.data else "",
                    "old_data_json": json.dumps(op.old_data, default=str)
                    if op.old_data
                    else "",
                },
            )

    def get_commit(self, commit_id: str) -> Commit:
        """Fetch a single commit by ID."""
        result = self._meta_graph.ro_query(
            schema.GET_COMMIT,
            params={"commit_id": commit_id},
        )
        if not result.result_set:
            raise CommitNotFoundError(commit_id)
        row = result.result_set[0]
        return Commit(
            commit_id=row[0],
            message=row[1],
            timestamp=row[2],
            parent_id=row[3],
            has_snapshot=row[4],
            branch=row[5],
        )

    def get_commits(self, branch: str = "main", limit: int = 20) -> list[Commit]:
        """Get commit history for a branch, newest first."""
        result = self._meta_graph.ro_query(
            schema.GET_ALL_COMMITS_FROM_HEAD,
            params={"branch_name": branch, "limit": limit},
        )
        commits = []
        for row in result.result_set:
            commits.append(Commit(
                commit_id=row[0],
                message=row[1],
                timestamp=row[2],
                parent_id=None,  # Not fetched in list query
                has_snapshot=row[3],
                branch=row[4],
            ))
        return commits

    def get_snapshot(self, commit_id: str) -> GraphSnapshot:
        """Fetch the snapshot for a specific commit."""
        result = self._meta_graph.ro_query(
            schema.GET_SNAPSHOT,
            params={"commit_id": commit_id},
        )
        if not result.result_set:
            raise CommitNotFoundError(commit_id)
        row = result.result_set[0]
        return GraphSnapshot.from_json(row[0], row[1])

    def get_nearest_snapshot(self, commit_id: str) -> tuple[str, GraphSnapshot]:
        """Find the nearest ancestor commit that has a snapshot."""
        result = self._meta_graph.ro_query(
            schema.FIND_NEAREST_SNAPSHOT,
            params={"commit_id": commit_id},
        )
        if not result.result_set:
            raise CommitNotFoundError(commit_id)
        row = result.result_set[0]
        return row[0], GraphSnapshot.from_json(row[1], row[2])

    def get_diff_entries(self, commit_id: str) -> list[DiffOp]:
        """Get all diff entries for a commit."""
        result = self._meta_graph.ro_query(
            schema.GET_DIFF_ENTRIES,
            params={"commit_id": commit_id},
        )
        ops = []
        for row in result.result_set:
            ops.append(DiffOp(
                op=OpType(row[0]),
                element_key=row[1],
                data=json.loads(row[2]) if row[2] else None,
                old_data=json.loads(row[3]) if row[3] else None,
            ))
        return ops

    def get_active_branch(self) -> Branch:
        """Get the currently active branch."""
        result = self._meta_graph.ro_query(schema.GET_ACTIVE_BRANCH)
        if not result.result_set:
            return Branch(name="main", head_commit_id=None, is_active=True)
        row = result.result_set[0]
        return Branch(name=row[0], head_commit_id=row[1], is_active=row[2])

    def get_branch(self, name: str) -> Branch:
        """Get a branch by name."""
        result = self._meta_graph.ro_query(
            schema.GET_BRANCH,
            params={"name": name},
        )
        if not result.result_set:
            raise BranchNotFoundError(name)
        row = result.result_set[0]
        return Branch(name=row[0], head_commit_id=row[1], is_active=row[2])

    def get_all_branches(self) -> list[Branch]:
        """Get all branches."""
        result = self._meta_graph.ro_query(schema.GET_ALL_BRANCHES)
        return [
            Branch(name=row[0], head_commit_id=row[1], is_active=row[2])
            for row in result.result_set
        ]

    def create_branch(self, name: str, head_commit_id: str | None) -> None:
        """Create a new branch pointing at the given commit."""
        self._meta_graph.query(
            schema.INIT_BRANCH,
            params={"name": name, "is_active": False},
        )
        if head_commit_id:
            self._meta_graph.query(
                schema.UPDATE_BRANCH_HEAD,
                params={"branch_name": name, "commit_id": head_commit_id},
            )

    def switch_active_branch(self, name: str) -> None:
        """Set a branch as active (deactivates all others)."""
        self._meta_graph.query(
            schema.SET_ACTIVE_BRANCH,
            params={"name": name},
        )

    def find_common_ancestor(self, commit_id_1: str, commit_id_2: str) -> str | None:
        """Find the lowest common ancestor of two commits."""
        result = self._meta_graph.ro_query(
            schema.FIND_COMMON_ANCESTOR,
            params={"commit_id_1": commit_id_1, "commit_id_2": commit_id_2},
        )
        if not result.result_set:
            return None
        return result.result_set[0][0]
