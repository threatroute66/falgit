"""Apply snapshots — restore a graph to a previous state."""

from __future__ import annotations

from falgit.models.types import EdgeState, GraphSnapshot, NodeState


def restore_snapshot(graph, snapshot: GraphSnapshot) -> None:
    """Wipe a graph and recreate it from a snapshot.

    Args:
        graph: A FalkorDB graph object.
        snapshot: The target state to restore.
    """
    # Delete all existing data
    graph.query("MATCH (n) DETACH DELETE n")

    if not snapshot.nodes and not snapshot.edges:
        return

    # Recreate nodes in batches
    _create_nodes(graph, list(snapshot.nodes.values()))

    # Recreate edges
    _create_edges(graph, list(snapshot.edges.values()), snapshot)


def _create_nodes(graph, nodes: list[NodeState], batch_size: int = 100) -> None:
    """Create nodes in batches using UNWIND."""
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i : i + batch_size]
        for node in batch:
            labels_str = ":" + ":".join(node.labels) if node.labels else ""
            props_str = _props_to_cypher(node.props)
            query = f"CREATE (n{labels_str} {props_str})"
            graph.query(query)


def _create_edges(
    graph, edges: list[EdgeState], snapshot: GraphSnapshot
) -> None:
    """Recreate edges by matching source and target nodes."""
    # Build a lookup: node_key -> (labels, props) for matching
    node_lookup: dict[str, NodeState] = snapshot.nodes

    for edge in edges:
        src_node = node_lookup.get(edge.src_key)
        dst_node = node_lookup.get(edge.dst_key)
        if not src_node or not dst_node:
            continue

        src_match = _node_match_clause("a", src_node)
        dst_match = _node_match_clause("b", dst_node)
        props_str = _props_to_cypher(edge.props)

        query = (
            f"MATCH {src_match}, {dst_match} "
            f"CREATE (a)-[r:{edge.rel_type} {props_str}]->(b)"
        )
        graph.query(query)


def _node_match_clause(alias: str, node: NodeState) -> str:
    """Build a MATCH clause that uniquely identifies a node by its labels and properties."""
    labels_str = ":" + ":".join(node.labels) if node.labels else ""
    props_str = _props_to_cypher(node.props)
    return f"({alias}{labels_str} {props_str})"


def _props_to_cypher(props: dict) -> str:
    """Convert a properties dict to a Cypher properties string."""
    if not props:
        return "{}"
    parts = []
    for k, v in props.items():
        parts.append(f"{k}: {_value_to_cypher(v)}")
    return "{" + ", ".join(parts) + "}"


def _value_to_cypher(value) -> str:
    """Convert a Python value to its Cypher literal representation."""
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        items = ", ".join(_value_to_cypher(v) for v in value)
        return f"[{items}]"
    if value is None:
        return "null"
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"
