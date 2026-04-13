"""Tests for the snapshot module."""

from falgit.core.snapshot import snapshot_graph


def test_snapshot_empty_graph(mock_graph):
    snap = snapshot_graph(mock_graph)
    assert snap.nodes == {}
    assert snap.edges == {}


def test_snapshot_nodes(populated_graph):
    snap = snapshot_graph(populated_graph)
    assert len(snap.nodes) == 2
    # Check that node keys are content-based hashes
    for key, node in snap.nodes.items():
        assert len(key) == 16  # sha256[:16]
        assert "Person" in node.labels


def test_snapshot_edges(populated_graph):
    snap = snapshot_graph(populated_graph)
    assert len(snap.edges) == 1
    edge = list(snap.edges.values())[0]
    assert edge.rel_type == "KNOWS"
    assert edge.props == {"since": 2020}


def test_snapshot_duplicate_nodes(mock_graph):
    """Nodes with identical labels+props get suffixed keys."""
    mock_graph.add_node(["Person"], {"name": "Alice"})
    mock_graph.add_node(["Person"], {"name": "Alice"})
    snap = snapshot_graph(mock_graph)
    assert len(snap.nodes) == 2
    keys = list(snap.nodes.keys())
    assert keys[0] != keys[1]


def test_snapshot_serialization(populated_graph):
    snap = snapshot_graph(populated_graph)
    nodes_json, edges_json = snap.to_json()
    from falgit.models.types import GraphSnapshot
    restored = GraphSnapshot.from_json(nodes_json, edges_json)
    assert len(restored.nodes) == len(snap.nodes)
    assert len(restored.edges) == len(snap.edges)
