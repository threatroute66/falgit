"""Falgit custom exceptions."""


class FalgitError(Exception):
    """Base exception for all falgit errors."""


class NotInitializedError(FalgitError):
    """Raised when operating on a graph that hasn't been initialized with falgit."""

    def __init__(self, graph_name: str):
        super().__init__(
            f"Graph '{graph_name}' is not initialized for falgit tracking. "
            f"Run 'falgit init {graph_name}' first."
        )
        self.graph_name = graph_name


class AlreadyInitializedError(FalgitError):
    """Raised when trying to init a graph that's already tracked."""

    def __init__(self, graph_name: str):
        super().__init__(
            f"Graph '{graph_name}' is already initialized for falgit tracking."
        )
        self.graph_name = graph_name


class CommitNotFoundError(FalgitError):
    """Raised when a commit ID doesn't exist."""

    def __init__(self, commit_id: str):
        super().__init__(f"Commit '{commit_id}' not found.")
        self.commit_id = commit_id


class BranchNotFoundError(FalgitError):
    """Raised when a branch name doesn't exist."""

    def __init__(self, branch_name: str):
        super().__init__(f"Branch '{branch_name}' not found.")
        self.branch_name = branch_name


class BranchExistsError(FalgitError):
    """Raised when trying to create a branch that already exists."""

    def __init__(self, branch_name: str):
        super().__init__(f"Branch '{branch_name}' already exists.")
        self.branch_name = branch_name


class MergeConflictError(FalgitError):
    """Raised when a merge encounters conflicts that cannot be auto-resolved."""

    def __init__(self, conflicts: list[dict]):
        self.conflicts = conflicts
        conflict_summary = ", ".join(c["element_key"] for c in conflicts[:5])
        if len(conflicts) > 5:
            conflict_summary += f" ... and {len(conflicts) - 5} more"
        super().__init__(
            f"Merge conflict on {len(conflicts)} element(s): {conflict_summary}"
        )


class NothingToCommitError(FalgitError):
    """Raised when there are no changes to commit."""

    def __init__(self):
        super().__init__("Nothing to commit — graph state matches last commit.")
