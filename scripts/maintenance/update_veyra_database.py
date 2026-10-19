import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from graph.connection import get_graph

BACKUP = Path("veyra-before-cleanup-20261018-062943.json")
BATCH = 10

if not BACKUP.exists():
    raise SystemExit(f"Backup not found: {BACKUP.resolve()}")

print("Reading backup...", flush=True)
with BACKUP.open(encoding="utf-8") as f:
    data = json.load(f)

raw_nodes = data.get("nodes", [])
raw_edges = data.get("relationships", [])

nodes = {}
for item in raw_nodes:
    props = item.get("properties") or {}
    if props.get("id") is None:
        continue
    node_id = str(props["id"])
    nodes[node_id] = {
        "id": node_id,
        "properties": props,
        "labels": item.get("labels") or [],
    }

edges = []
for item in raw_edges:
    source = str(item.get("source", ""))
    target = str(item.get("target", ""))
    rel_type = str(item.get("type", ""))

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", rel_type):
        raise SystemExit(f"Invalid relationship type: {rel_type!r}")

    if source not in nodes or target not in nodes:
        continue

    edges.append({
        "source": source,
        "target": target,
        "type": rel_type,
        "properties": item.get("properties") or {},
    })

print(f"Backup nodes: {len(nodes)}")
print(f"Backup relationships: {len(edges)}")
print("Backup relationship types:")
for rel, count in sorted(Counter(e["type"] for e in edges).items()):
    print(f"  {rel}: {count}")

graph = get_graph()

# 1. Snapshot the current graph before writing.
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
snapshot_path = Path("backups") / f"veyra-before-update-{stamp}.json"
snapshot_path.parent.mkdir(parents=True, exist_ok=True)

current_nodes = graph.query(
    "MATCH (n:Entity) RETURN labels(n), properties(n)"
).result_set
current_edges = graph.query(
    """
    MATCH (a:Entity)-[r]->(b:Entity)
    RETURN a.id, type(r), b.id, properties(r)
    """
).result_set

with snapshot_path.open("w", encoding="utf-8") as f:
    json.dump({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "nodes": [
            {"labels": row[0], "properties": row[1]}
            for row in current_nodes
        ],
        "relationships": [
            {
                "source": row[0],
                "type": row[1],
                "target": row[2],
                "properties": row[3],
            }
            for row in current_edges
        ],
    }, f, ensure_ascii=False)

print(
    f"Current graph snapshot saved: {snapshot_path} "
    f"({len(current_nodes)} nodes, {len(current_edges)} edges)",
    flush=True,
)

# 2. Restore/upsert nodes without deleting existing nodes.
node_rows = [
    {"id": n["id"], "properties": n["properties"]}
    for n in nodes.values()
]
for i in range(0, len(node_rows), BATCH):
    graph.query(
        """
        UNWIND $rows AS row
        MERGE (n:Entity {id: row.id})
        SET n += row.properties
        """,
        {"rows": node_rows[i:i + BATCH]},
    )

# 3. Restore the original labels.
labels_to_ids = defaultdict(list)
for node in nodes.values():
    for label in set(node["labels"]):
        if label == "Entity":
            continue
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", label):
            raise SystemExit(f"Invalid label: {label!r}")
        labels_to_ids[label].append(node["id"])

for label, ids in labels_to_ids.items():
    for i in range(0, len(ids), BATCH):
        graph.query(
            f"""
            UNWIND $ids AS node_id
            MATCH (n:Entity {{id: node_id}})
            SET n:{label}
            """,
            {"ids": ids[i:i + BATCH]},
        )

# 4. Restore relationships idempotently by type and endpoints.
by_type = defaultdict(list)
for edge in edges:
    by_type[edge["type"]].append(edge)

for rel_type, rels in sorted(by_type.items()):
    print(f"Restoring {rel_type}: {len(rels)}", flush=True)
    for i in range(0, len(rels), BATCH):
        graph.query(
            f"""
            UNWIND $rows AS row
            MATCH (a:Entity {{id: row.source}})
            MATCH (b:Entity {{id: row.target}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += row.properties
            """,
            {"rows": rels[i:i + BATCH]},
        )

# 5. Remove the synthetic scenario's spoke edges, not the scenario node.
# This prevents it from acting as the default visual hub.
result = graph.query(
    """
    MATCH (s:Scenario)
    WHERE toLower(trim(coalesce(s.name, ""))) = "synthetic social network"
    OPTIONAL MATCH (s)-[r:IN_SCENARIO]-()
    WITH collect(r) AS relationships
    UNWIND relationships AS rel
    WITH rel WHERE rel IS NOT NULL
    DELETE rel
    RETURN count(rel)
    """
).result_set

removed = result[0][0] if result else 0
print(f"Disconnected synthetic scenario spokes: {removed}", flush=True)

# 6. Report final database state.
node_count = graph.query(
    "MATCH (n:Entity) RETURN count(n)"
).result_set[0][0]
edge_count = graph.query(
    "MATCH (:Entity)-[r]->(:Entity) RETURN count(r)"
).result_set[0][0]
type_rows = graph.query(
    """
    MATCH (:Entity)-[r]->(:Entity)
    RETURN type(r), count(r)
    ORDER BY type(r)
    """
).result_set

print("\nDATABASE UPDATE FINISHED")
print(f"Snapshot: {snapshot_path}")
print(f"Entity nodes: {node_count}")
print(f"Relationships: {edge_count}")
print("Relationship counts:")
for rel, count in type_rows:
    print(f"  {rel}: {count}")
