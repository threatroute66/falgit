"""Cypher query templates for the falgit metadata graph."""

# Initialize metadata graph
INIT_META = """
CREATE (m:FalgitMeta {graph_name: $graph_name, created_at: $created_at, version: 1})
"""

INIT_BRANCH = """
CREATE (b:Branch {name: $name, is_active: $is_active})
"""

# Check if graph is initialized
CHECK_INIT = """
MATCH (m:FalgitMeta {graph_name: $graph_name}) RETURN m.graph_name
"""

# Commits
CREATE_COMMIT = """
CREATE (c:Commit {
    commit_id: $commit_id,
    message: $message,
    timestamp: $timestamp,
    has_snapshot: $has_snapshot,
    branch: $branch
})
RETURN c.commit_id
"""

LINK_COMMIT_PARENT = """
MATCH (child:Commit {commit_id: $child_id}), (parent:Commit {commit_id: $parent_id})
CREATE (child)-[:PARENT]->(parent)
"""

UPDATE_BRANCH_HEAD = """
MATCH (b:Branch {name: $branch_name})
OPTIONAL MATCH (b)-[old:HEAD]->()
DELETE old
WITH b
MATCH (c:Commit {commit_id: $commit_id})
CREATE (b)-[:HEAD]->(c)
"""

# Snapshots
CREATE_SNAPSHOT = """
MATCH (c:Commit {commit_id: $commit_id})
CREATE (s:Snapshot {commit_id: $commit_id, nodes_json: $nodes_json, edges_json: $edges_json})
CREATE (c)-[:HAS_SNAPSHOT]->(s)
"""

# Diff entries
CREATE_DIFF_ENTRY = """
MATCH (c:Commit {commit_id: $commit_id})
CREATE (d:DiffEntry {
    commit_id: $commit_id,
    op: $op,
    element_key: $element_key,
    data_json: $data_json,
    old_data_json: $old_data_json
})
CREATE (c)-[:HAS_DIFF]->(d)
"""

# Queries
GET_COMMITS_ON_BRANCH = """
MATCH (b:Branch {name: $branch_name})-[:HEAD]->(head:Commit)
MATCH path = (head)-[:PARENT*0..]->(ancestor:Commit)
WHERE ancestor.branch = $branch_name OR head = ancestor
WITH ancestor ORDER BY ancestor.timestamp DESC
LIMIT $limit
RETURN ancestor.commit_id, ancestor.message, ancestor.timestamp,
       ancestor.has_snapshot, ancestor.branch
"""

GET_ALL_COMMITS_FROM_HEAD = """
MATCH (b:Branch {name: $branch_name})-[:HEAD]->(head:Commit)
MATCH path = (head)-[:PARENT*0..]->(ancestor:Commit)
WITH ancestor ORDER BY ancestor.timestamp DESC
LIMIT $limit
RETURN ancestor.commit_id, ancestor.message, ancestor.timestamp,
       ancestor.has_snapshot, ancestor.branch
"""

GET_COMMIT = """
MATCH (c:Commit {commit_id: $commit_id})
OPTIONAL MATCH (c)-[:PARENT]->(p:Commit)
RETURN c.commit_id, c.message, c.timestamp, p.commit_id, c.has_snapshot, c.branch
"""

GET_SNAPSHOT = """
MATCH (s:Snapshot {commit_id: $commit_id})
RETURN s.nodes_json, s.edges_json
"""

GET_DIFF_ENTRIES = """
MATCH (c:Commit {commit_id: $commit_id})-[:HAS_DIFF]->(d:DiffEntry)
RETURN d.op, d.element_key, d.data_json, d.old_data_json
"""

# Branch queries
GET_ACTIVE_BRANCH = """
MATCH (b:Branch {is_active: true})
OPTIONAL MATCH (b)-[:HEAD]->(c:Commit)
RETURN b.name, c.commit_id, b.is_active
"""

GET_BRANCH = """
MATCH (b:Branch {name: $name})
OPTIONAL MATCH (b)-[:HEAD]->(c:Commit)
RETURN b.name, c.commit_id, b.is_active
"""

GET_ALL_BRANCHES = """
MATCH (b:Branch)
OPTIONAL MATCH (b)-[:HEAD]->(c:Commit)
RETURN b.name, c.commit_id, b.is_active
ORDER BY b.name
"""

SET_ACTIVE_BRANCH = """
MATCH (b:Branch) SET b.is_active = false
WITH b
MATCH (target:Branch {name: $name}) SET target.is_active = true
"""

# Find nearest snapshot walking up the parent chain
FIND_NEAREST_SNAPSHOT = """
MATCH (start:Commit {commit_id: $commit_id})
MATCH path = (start)-[:PARENT*0..]->(ancestor:Commit)
WHERE ancestor.has_snapshot = true
WITH ancestor, length(path) AS dist
ORDER BY dist ASC
LIMIT 1
MATCH (ancestor)-[:HAS_SNAPSHOT]->(s:Snapshot)
RETURN s.commit_id, s.nodes_json, s.edges_json
"""

# Find common ancestor of two commits
FIND_COMMON_ANCESTOR = """
MATCH path1 = (c1:Commit {commit_id: $commit_id_1})-[:PARENT*0..]->(a:Commit)
MATCH path2 = (c2:Commit {commit_id: $commit_id_2})-[:PARENT*0..]->(a)
WITH a, length(path1) + length(path2) AS total_dist
ORDER BY total_dist ASC
LIMIT 1
RETURN a.commit_id
"""
