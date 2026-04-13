"""FalgitRepo — main orchestrator for git-like operations on FalkorDB graphs."""

from __future__ import annotations

import time
import uuid

from falgit.core.apply import restore_snapshot
from falgit.core.diff import compute_diff, diff_to_status
from falgit.core.snapshot import snapshot_graph
from falgit.errors import (
    AlreadyInitializedError,
    BranchExistsError,
    BranchNotFoundError,
    MergeConflictError,
    NothingToCommitError,
    NotInitializedError,
)
from falgit.meta.store import MetadataStore
from falgit.models.types import (
    Branch,
    Commit,
    DiffOp,
    GraphSnapshot,
    MergeResult,
    Status,
)

SNAPSHOT_INTERVAL = 10


def _generate_commit_id() -> str:
    return uuid.uuid4().hex[:12]


class FalgitRepo:
    """Git-like version control for a FalkorDB graph."""

    def __init__(self, db, graph_name: str):
        self._db = db
        self._graph_name = graph_name
        self._graph = db.select_graph(graph_name)
        self._store = MetadataStore(db, graph_name)

        if not self._store.is_initialized():
            raise NotInitializedError(graph_name)

    @classmethod
    def init(cls, db, graph_name: str) -> FalgitRepo:
        """Enable falgit tracking on an existing graph.

        Creates the metadata graph and takes an initial snapshot as commit 0.
        """
        store = MetadataStore(db, graph_name)
        if store.is_initialized():
            raise AlreadyInitializedError(graph_name)

        now = int(time.time())
        store.initialize(now)

        # Take initial snapshot
        graph = db.select_graph(graph_name)
        snap = snapshot_graph(graph)

        commit = Commit(
            commit_id=_generate_commit_id(),
            message="Initial falgit commit",
            timestamp=now,
            parent_id=None,
            has_snapshot=True,
            branch="main",
        )

        store.save_commit(commit, snapshot=snap, diff_ops=[])

        return cls(db, graph_name)

    def commit(self, message: str) -> Commit:
        """Commit the current graph state.

        Takes a snapshot, computes a diff from the last commit, and stores both.
        """
        branch = self._store.get_active_branch()
        current_snap = snapshot_graph(self._graph)

        # Get the last snapshot to compute diff
        previous_snap = self._get_head_snapshot(branch)
        diff_ops = compute_diff(previous_snap, current_snap)

        if not diff_ops:
            raise NothingToCommitError()

        # Determine commit number for snapshot interval
        commits = self._store.get_commits(branch.name, limit=1000)
        commit_number = len(commits)
        should_snapshot = (commit_number % SNAPSHOT_INTERVAL == 0)

        commit = Commit(
            commit_id=_generate_commit_id(),
            message=message,
            timestamp=int(time.time()),
            parent_id=branch.head_commit_id,
            has_snapshot=should_snapshot or True,  # Always snapshot for now (MVP)
            branch=branch.name,
        )

        self._store.save_commit(
            commit,
            snapshot=current_snap if commit.has_snapshot else None,
            diff_ops=diff_ops,
        )

        return commit

    def log(self, limit: int = 20) -> list[Commit]:
        """Get commit history for the active branch."""
        branch = self._store.get_active_branch()
        return self._store.get_commits(branch.name, limit=limit)

    def status(self) -> Status:
        """Show changes since the last commit."""
        branch = self._store.get_active_branch()
        current_snap = snapshot_graph(self._graph)
        previous_snap = self._get_head_snapshot(branch)
        diff_ops = compute_diff(previous_snap, current_snap)
        return diff_to_status(diff_ops)

    def diff(
        self, commit_a: str | None = None, commit_b: str | None = None
    ) -> list[DiffOp]:
        """Compare two commits or current state vs a commit.

        - Both None: diff last commit vs current state.
        - commit_a only: diff commit_a vs current state.
        - Both specified: diff commit_a vs commit_b.
        """
        if commit_a is None and commit_b is None:
            branch = self._store.get_active_branch()
            old_snap = self._get_head_snapshot(branch)
            new_snap = snapshot_graph(self._graph)
        elif commit_b is None:
            old_snap = self._store.get_snapshot(commit_a)
            new_snap = snapshot_graph(self._graph)
        else:
            old_snap = self._store.get_snapshot(commit_a)
            new_snap = self._store.get_snapshot(commit_b)

        return compute_diff(old_snap, new_snap)

    def checkout(self, commit_id: str) -> None:
        """Restore the graph to the state at a given commit."""
        # Verify commit exists
        self._store.get_commit(commit_id)

        # Get the snapshot (either direct or nearest ancestor)
        try:
            snapshot = self._store.get_snapshot(commit_id)
        except Exception:
            _, snapshot = self._store.get_nearest_snapshot(commit_id)

        restore_snapshot(self._graph, snapshot)

    def branch(self, name: str) -> Branch:
        """Create a new branch from the current HEAD."""
        # Check it doesn't already exist
        try:
            self._store.get_branch(name)
            raise BranchExistsError(name)
        except BranchNotFoundError:
            pass

        active = self._store.get_active_branch()
        self._store.create_branch(name, active.head_commit_id)
        return self._store.get_branch(name)

    def list_branches(self) -> list[Branch]:
        """List all branches."""
        return self._store.get_all_branches()

    def switch(self, branch_name: str) -> None:
        """Switch to a different branch, restoring the graph to that branch's HEAD."""
        branch = self._store.get_branch(branch_name)
        self._store.switch_active_branch(branch_name)

        # Restore graph to the branch's HEAD state
        if branch.head_commit_id:
            self.checkout(branch.head_commit_id)

    def merge(self, branch_name: str) -> MergeResult:
        """Merge a branch into the active branch.

        Uses three-way merge: find common ancestor, compute diffs from ancestor
        to each branch head, apply non-conflicting changes.
        Raises MergeConflictError if conflicts are detected.
        """
        source_branch = self._store.get_branch(branch_name)
        target_branch = self._store.get_active_branch()

        if not source_branch.head_commit_id or not target_branch.head_commit_id:
            raise ValueError("Cannot merge branches without commits.")

        # Find common ancestor
        ancestor_id = self._store.find_common_ancestor(
            target_branch.head_commit_id, source_branch.head_commit_id
        )

        if ancestor_id is None:
            raise ValueError("No common ancestor found between branches.")

        # Get snapshots
        ancestor_snap = self._store.get_snapshot(ancestor_id)
        source_snap = self._store.get_snapshot(source_branch.head_commit_id)
        target_snap = self._store.get_snapshot(target_branch.head_commit_id)

        # Compute diffs from ancestor to each branch
        source_diff = compute_diff(ancestor_snap, source_snap)
        target_diff = compute_diff(ancestor_snap, target_snap)

        # Detect conflicts: same element_key modified in both branches
        source_keys = {op.element_key: op for op in source_diff}
        target_keys = {op.element_key: op for op in target_diff}

        conflicts = []
        for key in source_keys.keys() & target_keys.keys():
            s_op = source_keys[key]
            t_op = target_keys[key]
            # Same change in both branches is not a conflict
            if s_op.op == t_op.op and s_op.data == t_op.data:
                continue
            conflicts.append({
                "element_key": key,
                "source_op": s_op.to_dict(),
                "target_op": t_op.to_dict(),
            })

        if conflicts:
            raise MergeConflictError(conflicts)

        # Apply source branch changes to current graph
        # Start from target snapshot, add source-only changes
        merged_snap = self._apply_merge(target_snap, source_diff, target_keys)
        restore_snapshot(self._graph, merged_snap)

        # Create merge commit
        auto_resolved = len(source_keys.keys() & target_keys.keys())
        all_diff_ops = compute_diff(target_snap, merged_snap)

        merge_commit = Commit(
            commit_id=_generate_commit_id(),
            message=f"Merge branch '{branch_name}' into {target_branch.name}",
            timestamp=int(time.time()),
            parent_id=target_branch.head_commit_id,
            has_snapshot=True,
            branch=target_branch.name,
        )

        self._store.save_commit(merge_commit, snapshot=merged_snap, diff_ops=all_diff_ops)

        return MergeResult(
            commit=merge_commit,
            auto_resolved=auto_resolved,
            source_branch=branch_name,
            target_branch=target_branch.name,
        )

    def _get_head_snapshot(self, branch: Branch) -> GraphSnapshot:
        """Get the snapshot at the HEAD of a branch."""
        if not branch.head_commit_id:
            return GraphSnapshot.empty()
        return self._store.get_snapshot(branch.head_commit_id)

    def _apply_merge(
        self,
        target_snap: GraphSnapshot,
        source_diff: list[DiffOp],
        target_keys: dict[str, DiffOp],
    ) -> GraphSnapshot:
        """Apply source branch changes to the target snapshot.

        Only applies changes from source that don't overlap with target changes.
        """
        from falgit.models.types import EdgeState, NodeState, OpType

        merged_nodes = dict(target_snap.nodes)
        merged_edges = dict(target_snap.edges)

        for op in source_diff:
            # Skip if this key was also changed in target (already handled above)
            if op.element_key in target_keys:
                continue

            if op.op == OpType.ADD_NODE and op.data:
                ns = NodeState.from_dict(op.data)
                merged_nodes[op.element_key] = ns
            elif op.op == OpType.DEL_NODE:
                merged_nodes.pop(op.element_key, None)
            elif op.op == OpType.MOD_NODE and op.data:
                ns = NodeState.from_dict(op.data)
                merged_nodes[op.element_key] = ns
            elif op.op == OpType.ADD_EDGE and op.data:
                es = EdgeState.from_dict(op.data)
                merged_edges[op.element_key] = es
            elif op.op == OpType.DEL_EDGE:
                merged_edges.pop(op.element_key, None)
            elif op.op == OpType.MOD_EDGE and op.data:
                es = EdgeState.from_dict(op.data)
                merged_edges[op.element_key] = es

        return GraphSnapshot(nodes=merged_nodes, edges=merged_edges)
