# falgit

Git-like version control for [FalkorDB](https://www.falkordb.com/) graphs.

FalkorDB does not have built-in graph-level version control. **falgit** adds change tracking, commit history, branching, and merging to any FalkorDB graph.

## Features

- **init** — Enable version tracking on an existing graph
- **commit** — Snapshot the current graph state with a message
- **log** — View commit history
- **status** — See what changed since the last commit
- **diff** — Compare two commits or current state vs a commit
- **checkout** — Restore a graph to any previous commit
- **branch** — Create named branches
- **merge** — Three-way merge with conflict detection

## Installation

```bash
git clone https://github.com/falgit/falgit.git
cd falgit
pip install -e .
```

Requires Python 3.8+ and a running FalkorDB instance (Redis-compatible).

## Quick Start

```python
from falkordb import FalkorDB
from falgit import FalgitRepo

# Connect to FalkorDB
db = FalkorDB(host="localhost", port=6379)

# Create some data
graph = db.select_graph("my_graph")
graph.query("CREATE (a:Person {name: 'Alice'})-[:KNOWS]->(b:Person {name: 'Bob'})")

# Initialize falgit tracking
repo = FalgitRepo.init(db, "my_graph")

# Make changes
graph.query("CREATE (c:Person {name: 'Charlie'})")

# Check status
status = repo.status()
print(f"Changes: {status.total_changes}")

# Commit
commit = repo.commit("Add Charlie")
print(f"Committed: {commit.commit_id}")

# View history
for c in repo.log():
    print(f"  {c.commit_id} — {c.message}")

# Restore to a previous state
commits = repo.log()
repo.checkout(commits[-1].commit_id)
```

## CLI Usage

```bash
# Initialize tracking
falgit init my_graph --host localhost --port 6379

# Check status
falgit status my_graph

# Commit changes
falgit commit my_graph -m "Add new nodes"

# View history
falgit log my_graph

# Show differences
falgit diff my_graph

# Restore to a previous commit
falgit checkout my_graph abc123def456

# Branching
falgit branch my_graph feature-x
falgit switch my_graph feature-x
falgit merge my_graph feature-x
```

### Environment Variables

- `FALKORDB_HOST` — FalkorDB host (default: `localhost`)
- `FALKORDB_PORT` — FalkorDB port (default: `6379`)

## How It Works

falgit does not store any data on the local filesystem. All version control metadata is stored inside your FalkorDB instance as a companion graph named `_falgit_{graphname}`. This graph tracks:

- **Commits** with timestamps, messages, and parent references
- **Snapshots** — full serialized graph state at each commit
- **Diffs** — granular per-node/edge change records
- **Branches** — named pointers to commit heads

> **Note:** Because falgit data lives entirely within FalkorDB, if the FalkorDB instance is lost or destroyed, all version history is lost with it. Consider backing up your FalkorDB data (e.g., RDB/AOF snapshots) to protect both your graphs and their falgit history.

### Node Identity

Since FalkorDB internal IDs are not stable across deletions, falgit uses **content-based hashing** to identify nodes and edges. A node's identity key is derived from its labels and properties. This means:

- Two nodes with identical labels and properties are treated as the same node
- If you need to distinguish truly identical nodes, add a unique property (e.g., a UUID)

### Limitations

- **Large graphs**: Snapshotting queries all nodes/edges. For very large graphs (>100k nodes), commits may be slow.
- **Concurrent modifications**: If the graph is modified during a snapshot, the result may be inconsistent.
- **Duplicate nodes**: Nodes with identical labels and properties share the same identity key.

## Development

```bash
git clone https://github.com/falgit/falgit.git
cd falgit
pip install -e ".[dev]"
pytest
```

## License

MIT
