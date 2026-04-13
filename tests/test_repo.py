"""Tests for the FalgitRepo orchestrator (using mocks)."""

from unittest.mock import MagicMock, patch

from falgit.models.types import NodeState, GraphSnapshot


class TestRepoInit:
    def test_init_creates_metadata(self):
        """Test that init creates the metadata graph structure."""
        from falgit.meta.store import MetadataStore
        from falgit.repo import FalgitRepo

        mock_db = MagicMock()
        mock_graph = MagicMock()
        mock_db.select_graph.return_value = mock_graph

        # is_initialized returns False first (in init), then True (in constructor)
        with patch.object(MetadataStore, "is_initialized", side_effect=[False, True]):
            with patch.object(MetadataStore, "initialize"):
                with patch.object(MetadataStore, "save_commit"):
                    with patch(
                        "falgit.repo.snapshot_graph",
                        return_value=GraphSnapshot.empty(),
                    ):
                        repo = FalgitRepo.init(mock_db, "test")
                        assert repo is not None


class TestDiffComputation:
    def test_compute_diff_detects_additions(self):
        """Verify diff detects new nodes."""
        from falgit.core.diff import compute_diff
        from falgit.models.types import OpType

        old = GraphSnapshot.empty()
        ns = NodeState(labels=("Person",), props={"name": "Test"})
        new = GraphSnapshot(nodes={ns.key: ns}, edges={})

        ops = compute_diff(old, new)
        assert len(ops) == 1
        assert ops[0].op == OpType.ADD_NODE

    def test_compute_diff_detects_deletions(self):
        """Verify diff detects removed nodes."""
        from falgit.core.diff import compute_diff
        from falgit.models.types import OpType

        ns = NodeState(labels=("Person",), props={"name": "Test"})
        old = GraphSnapshot(nodes={ns.key: ns}, edges={})
        new = GraphSnapshot.empty()

        ops = compute_diff(old, new)
        assert len(ops) == 1
        assert ops[0].op == OpType.DEL_NODE
