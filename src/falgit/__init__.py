"""falgit — Git-like version control for FalkorDB graphs."""

from falgit.errors import (
    AlreadyInitializedError,
    BranchExistsError,
    BranchNotFoundError,
    CommitNotFoundError,
    FalgitError,
    MergeConflictError,
    NothingToCommitError,
    NotInitializedError,
)
from falgit.models.types import (
    Branch,
    Commit,
    DiffOp,
    EdgeState,
    GraphSnapshot,
    MergeResult,
    NodeState,
    OpType,
    Status,
)
from falgit.repo import FalgitRepo

__all__ = [
    "FalgitRepo",
    "FalgitError",
    "NotInitializedError",
    "AlreadyInitializedError",
    "CommitNotFoundError",
    "BranchNotFoundError",
    "BranchExistsError",
    "MergeConflictError",
    "NothingToCommitError",
    "Commit",
    "Branch",
    "DiffOp",
    "OpType",
    "NodeState",
    "EdgeState",
    "GraphSnapshot",
    "MergeResult",
    "Status",
]
