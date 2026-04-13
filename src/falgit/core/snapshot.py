"""Graph snapshotting — extract full state from a FalkorDB graph."""

from __future__ import annotations

from collections import Counter

from falgit.models.types import EdgeState, GraphSnapshot, NodeState, node_key


def snapshot_graph(graph) -> GraphSnapshot:
    """Take a complete snapshot of a FalkorDB graph.

    Args:
        graph: A FalkorDB graph object (from db.select_graph()).

    Returns:
        A GraphSnapshot containing all nodes and edges with stable keys.
    """
    nodes, id_to_key = _snapshot_nodes(graph)
    edges = _snapshot_edges(graph, id_to_key)
    return GraphSnapshot(nodes=nodes, edges=edges)


def _snapshot_nodes(graph) -> tuple[dict[str, NodeState], dict[int, str]]:
    """Query all nodes and build keyed node map.

    Returns:
        Tuple of (nodes dict keyed by stable key, mapping of internal id -> key).
    """
    result = graph.ro_query("MATCH (n) RETURN id(n), labels(n), properties(n)")

    nodes: dict[str, NodeState] = {}
    id_to_key: dict[int, str] = {}
    key_counter: Counter[str] = Counter()

    for row in result.result_set:
        internal_id = row[0]
        labels = tuple(sorted(row[1]))
        props = row[2] if row[2] else {}

        base_key = node_key(list(labels), props)
        count = key_counter[base_key]
        key_counter[base_key] += 1

        # Suffix duplicates to ensure uniqueness
        stable_key = f"{base_key}_{count}" if count > 0 else base_key

        ns = NodeState(labels=labels, props=props, key=stable_key)
        nodes[stable_key] = ns
        id_to_key[internal_id] = stable_key

    return nodes, id_to_key


def _snapshot_edges(graph, id_to_key: dict[int, str]) -> dict[str, EdgeState]:
    """Query all edges and build keyed edge map."""
    result = graph.ro_query(
        "MATCH (a)-[r]->(b) RETURN type(r), properties(r), id(a), id(b)"
    )

    edges: dict[str, EdgeState] = {}
    key_counter: Counter[str] = Counter()

    for row in result.result_set:
        rel_type = row[0]
        props = row[1] if row[1] else {}
        src_id = row[2]
        dst_id = row[3]

        src_key = id_to_key.get(src_id, f"unknown_{src_id}")
        dst_key = id_to_key.get(dst_id, f"unknown_{dst_id}")

        es = EdgeState(rel_type=rel_type, src_key=src_key, dst_key=dst_key, props=props)
        base_key = es.key

        count = key_counter[base_key]
        key_counter[base_key] += 1

        stable_key = f"{base_key}_{count}" if count > 0 else base_key
        es = EdgeState(
            rel_type=rel_type,
            src_key=src_key,
            dst_key=dst_key,
            props=props,
            key=stable_key,
        )
        edges[stable_key] = es

    return edges
