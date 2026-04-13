"""Tests for the diff module."""

from falgit.core.diff import compute_diff, diff_to_status
from falgit.models.types import EdgeState, GraphSnapshot, NodeState, OpType


def test_diff_empty_to_empty():
    old = GraphSnapshot.empty()
    new = GraphSnapshot.empty()
    assert compute_diff(old, new) == []


def test_diff_add_node():
    old = GraphSnapshot.empty()
    ns = NodeState(labels=("Person",), props={"name": "Alice"})
    new = GraphSnapshot(nodes={ns.key: ns}, edges={})
    ops = compute_diff(old, new)
    assert len(ops) == 1
    assert ops[0].op == OpType.ADD_NODE
    assert ops[0].element_key == ns.key


def test_diff_delete_node():
    ns = NodeState(labels=("Person",), props={"name": "Alice"})
    old = GraphSnapshot(nodes={ns.key: ns}, edges={})
    new = GraphSnapshot.empty()
    ops = compute_diff(old, new)
    assert len(ops) == 1
    assert ops[0].op == OpType.DEL_NODE


def test_diff_modify_node():
    ns_old = NodeState(labels=("Person",), props={"name": "Alice", "age": 30}, key="fixed_key")
    ns_new = NodeState(labels=("Person",), props={"name": "Alice", "age": 31}, key="fixed_key")
    old = GraphSnapshot(nodes={"fixed_key": ns_old}, edges={})
    new = GraphSnapshot(nodes={"fixed_key": ns_new}, edges={})
    ops = compute_diff(old, new)
    assert len(ops) == 1
    assert ops[0].op == OpType.MOD_NODE


def test_diff_add_edge():
    ns1 = NodeState(labels=("Person",), props={"name": "Alice"})
    ns2 = NodeState(labels=("Person",), props={"name": "Bob"})
    nodes = {ns1.key: ns1, ns2.key: ns2}

    es = EdgeState(rel_type="KNOWS", src_key=ns1.key, dst_key=ns2.key, props={})
    old = GraphSnapshot(nodes=nodes, edges={})
    new = GraphSnapshot(nodes=nodes, edges={es.key: es})
    ops = compute_diff(old, new)
    assert len(ops) == 1
    assert ops[0].op == OpType.ADD_EDGE


def test_diff_to_status():
    ns = NodeState(labels=("Person",), props={"name": "Alice"})
    old = GraphSnapshot.empty()
    new = GraphSnapshot(nodes={ns.key: ns}, edges={})
    ops = compute_diff(old, new)
    status = diff_to_status(ops)
    assert len(status.added_nodes) == 1
    assert status.total_changes == 1
    assert not status.is_clean


def test_diff_no_changes():
    ns = NodeState(labels=("Person",), props={"name": "Alice"})
    snap = GraphSnapshot(nodes={ns.key: ns}, edges={})
    ops = compute_diff(snap, snap)
    assert ops == []
    status = diff_to_status(ops)
    assert status.is_clean
