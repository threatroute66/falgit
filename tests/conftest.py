"""Test fixtures for falgit."""

import pytest


class MockResultSet:
    """Mock FalkorDB query result."""

    def __init__(self, rows=None):
        self.result_set = rows or []


class MockGraph:
    """Mock FalkorDB graph for unit testing without a live server."""

    def __init__(self, name="test_graph"):
        self.name = name
        self._nodes = {}  # id -> (labels, props)
        self._edges = {}  # id -> (type, props, src_id, dst_id)
        self._next_id = 1
        self._queries = []

    def query(self, q, params=None):
        self._queries.append((q, params))
        return MockResultSet()

    def ro_query(self, q, params=None):
        self._queries.append((q, params))

        # Simulate node query
        if "RETURN id(n), labels(n), properties(n)" in q:
            rows = [
                [nid, list(data[0]), data[1]]
                for nid, data in self._nodes.items()
            ]
            return MockResultSet(rows)

        # Simulate edge query
        if "RETURN type(r), properties(r), id(a), id(b)" in q:
            rows = [
                [data[0], data[1], data[2], data[3]]
                for data in self._edges.values()
            ]
            return MockResultSet(rows)

        return MockResultSet()

    def delete(self):
        self._nodes = {}
        self._edges = {}

    def add_node(self, labels, props):
        """Helper to add a node to the mock graph."""
        nid = self._next_id
        self._next_id += 1
        self._nodes[nid] = (tuple(sorted(labels)), props)
        return nid

    def add_edge(self, rel_type, props, src_id, dst_id):
        """Helper to add an edge to the mock graph."""
        eid = self._next_id
        self._next_id += 1
        self._edges[eid] = (rel_type, props, src_id, dst_id)
        return eid


@pytest.fixture
def mock_graph():
    """Provide a mock FalkorDB graph."""
    return MockGraph()


@pytest.fixture
def populated_graph():
    """Provide a mock graph with some data."""
    g = MockGraph()
    alice_id = g.add_node(["Person"], {"name": "Alice", "age": 30})
    bob_id = g.add_node(["Person"], {"name": "Bob", "age": 25})
    g.add_edge("KNOWS", {"since": 2020}, alice_id, bob_id)
    return g
