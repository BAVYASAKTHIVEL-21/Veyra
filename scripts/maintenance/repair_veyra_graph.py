import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from graph.connection import get_graph

BACKUP = Path("veyra-before-cleanup-20261018-062943.json")
BATCH = 200

if not BACKUP.exists():
    raise SystemExit(f"Cannot find backup: {BACKUP.resolve()}")

# Load and validate the backup before touching the live graph.
print("Loading backup...", flush=True)
with BACKUP.open(encoding="utf-8") as f:
    data = json.load(f)

node_map = {}
for item in data.get("nodes", []):
    props = item.get("properties") or {}
    if props.get("id") is not None:
        node_map[str(props["id"])] = {
            "id": str(props["id"]),
            "properties": props,
            "labels": item.get("labels") or [],
        }

backup_edges = []
for item in data.get("relationships", []):
    source = str(item.get("source", ""))
    target = str(item.get("target", ""))
    rel_type = str(item.get("type", ""))

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", rel_type):
        raise SystemExit(f"Invalid relationship type: {rel_type!r}")

    if source in node_map and target in node_map:
        backup_edges.append({
            "source": source,
            "target": target,
            "type": rel_type,
            "properties": item.get("properties") or {},
        })

graph = get_graph()

# Snapshot the current live graph first.
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
snapshot_path = Path("backups") / f"veyra-pre-repair-{stamp}.json"
snapshot_path.parent.mkdir(parents=True, exist_ok=True)

live_nodes = graph.query(
    "MATCH (n:Entity) RETURN labels(n), properties(n)"
).result_set
live_edges = graph.query(
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
            for row in live_nodes
        ],
        "relationships": [
            {
                "source": row[0],
                "type": row[1],
                "target": row[2],
                "properties": row[3],
            }
            for row in live_edges
        ],
    }, f, ensure_ascii=False)

print(f"Live snapshot saved: {snapshot_path}", flush=True)
print(f"Live graph before repair: {len(live_nodes)} nodes, {len(live_edges)} edges")

# Restore missing backup nodes and labels, without deleting live records.
node_rows = [
    {"id": n["id"], "properties": n["properties"]}
    for n in node_map.values()
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

labels_to_ids = defaultdict(list)
for node in node_map.values():
    for label in set(node["labels"]):
        if label == "Entity":
            continue
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", label):
            raise SystemExit(f"Invalid label in backup: {label!r}")
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

# Restore every backed-up relationship, not just a hand-picked subset.
by_type = defaultdict(list)
for edge in backup_edges:
    by_type[edge["type"]].append(edge)

for rel_type, edges in sorted(by_type.items()):
    print(f"Restoring {rel_type}: {len(edges)} backup edges", flush=True)
    for i in range(0, len(edges), BATCH):
        graph.query(
            f"""
            UNWIND $rows AS row
            MATCH (a:Entity {{id: row.source}})
            MATCH (b:Entity {{id: row.target}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += row.properties
            """,
            {"rows": edges[i:i + BATCH]},
        )

# Link cases to reports about the exact same message.
# Each report remains its own node with its own reporter and reason.
graph.query(
    """
    MATCH (c:Entity:Case)-[:CONCERNS_MESSAGE]->(m)
          <-[:ABOUT_MESSAGE]-(r:Entity:Report)
    MERGE (c)-[:HAS_REPORT]->(r)
    """
)

# Also link a case to reports about an account explicitly involved in it.
graph.query(
    """
    MATCH (c:Entity:Case)-[:INVOLVES_ACCOUNT]->(a:Entity:Account)
          <-[:REPORTS_ACCOUNT]-(r:Entity:Report)
    MERGE (c)-[:HAS_REPORT]->(r)
    """
)

# Link cases to saved investigations only when the saved record explicitly
# carries the matching case_id. Do not guess from similar names.
graph.query(
    """
    MATCH (c:Entity:Case), (i:Entity:Investigation)
    WHERE i.case_id = c.id
    MERGE (c)-[:HAS_INVESTIGATION]->(i)
    """
)

# Deduplicate parallel edges with identical type, direction and endpoints.
# Separate report nodes and different relationships are retained.
print("Checking duplicate edges...", flush=True)
groups = graph.query(
    """
    MATCH (a:Entity)-[r]->(b:Entity)
    WITH a.id AS source, type(r) AS rel_type, b.id AS target,
         count(r) AS copies
    WHERE copies > 1
    RETURN source, rel_type, target, copies
    """
).result_set

removed = 0
for source, rel_type, target, copies in groups:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(rel_type)):
        continue

    # Keep one relationship and remove only extra copies.
    result = graph.query(
        f"""
        MATCH (a:Entity {{id: $source}})
              -[r:{rel_type}]->
              (b:Entity {{id: $target}})
        WITH collect(r) AS relationships
        UNWIND relationships[1..] AS duplicate
        DELETE duplicate
        RETURN count(*) 
        """,
        {"source": source, "target": target},
    ).result_set
    if result:
        removed += int(result[0][0] or 0)

# Final counts.
final_nodes = graph.query(
    "MATCH (n:Entity) RETURN count(n)"
).result_set[0][0]
final_edges = graph.query(
    "MATCH (:Entity)-[r]->(:Entity) RETURN count(r)"
).result_set[0][0]
type_rows = graph.query(
    """
    MATCH (:Entity)-[r]->(:Entity)
    RETURN type(r), count(r)
    ORDER BY type(r)
    """
).result_set

print("\nREPAIR COMPLETE")
print(f"Snapshot: {snapshot_path}")
print(f"Duplicate edges removed: {removed}")
print(f"Final nodes: {final_nodes}")
print(f"Final edges: {final_edges}")
print("Relationship counts:")
for rel_type, count in type_rows:
    print(f"  {rel_type}: {count}")
