"""Diff computation between two graph snapshots."""

from __future__ import annotations

from falgit.models.types import DiffOp, GraphSnapshot, OpType, Status


def compute_diff(old: GraphSnapshot, new: GraphSnapshot) -> list[DiffOp]:
    """Compute the list of changes needed to go from old to new.

    Args:
        old: The previous graph state.
        new: The current graph state.

    Returns:
        List of DiffOp describing all changes.
    """
    ops: list[DiffOp] = []

    # Node diffs
    old_node_keys = set(old.nodes.keys())
    new_node_keys = set(new.nodes.keys())

    for key in new_node_keys - old_node_keys:
        ops.append(DiffOp(
            op=OpType.ADD_NODE,
            element_key=key,
            data=new.nodes[key].to_dict(),
        ))

    for key in old_node_keys - new_node_keys:
        ops.append(DiffOp(
            op=OpType.DEL_NODE,
            element_key=key,
            old_data=old.nodes[key].to_dict(),
        ))

    for key in old_node_keys & new_node_keys:
        old_node = old.nodes[key]
        new_node = new.nodes[key]
        if old_node.props != new_node.props or old_node.labels != new_node.labels:
            ops.append(DiffOp(
                op=OpType.MOD_NODE,
                element_key=key,
                data=new_node.to_dict(),
                old_data=old_node.to_dict(),
            ))

    # Edge diffs
    old_edge_keys = set(old.edges.keys())
    new_edge_keys = set(new.edges.keys())

    for key in new_edge_keys - old_edge_keys:
        ops.append(DiffOp(
            op=OpType.ADD_EDGE,
            element_key=key,
            data=new.edges[key].to_dict(),
        ))

    for key in old_edge_keys - new_edge_keys:
        ops.append(DiffOp(
            op=OpType.DEL_EDGE,
            element_key=key,
            old_data=old.edges[key].to_dict(),
        ))

    for key in old_edge_keys & new_edge_keys:
        old_edge = old.edges[key]
        new_edge = new.edges[key]
        if old_edge.props != new_edge.props:
            ops.append(DiffOp(
                op=OpType.MOD_EDGE,
                element_key=key,
                data=new_edge.to_dict(),
                old_data=old_edge.to_dict(),
            ))

    return ops


def diff_to_status(ops: list[DiffOp]) -> Status:
    """Convert a list of DiffOps into a Status summary."""
    status = Status()
    for op in ops:
        match op.op:
            case OpType.ADD_NODE:
                status.added_nodes.append(op.element_key)
            case OpType.DEL_NODE:
                status.deleted_nodes.append(op.element_key)
            case OpType.MOD_NODE:
                status.modified_nodes.append(op.element_key)
            case OpType.ADD_EDGE:
                status.added_edges.append(op.element_key)
            case OpType.DEL_EDGE:
                status.deleted_edges.append(op.element_key)
            case OpType.MOD_EDGE:
                status.modified_edges.append(op.element_key)
    return status
