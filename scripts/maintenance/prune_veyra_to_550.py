import json
from datetime import datetime, timezone
from pathlib import Path
from graph.connection import get_graph

TARGET = 550
BATCH_SIZE = 50
graph = get_graph()

print("Reading current VEYRA graph...")
node_rows = graph.query("""
    MATCH (n)
    RETURN id(n), labels(n), properties(n)
""").result_set

nodes = [
    {"internal_id": row[0], "labels": row[1], "properties": row[2]}
    for row in node_rows
]

rel_rows = graph.query("""
    MATCH (a)-[r]->(b)
    RETURN id(a), id(b), type(r), properties(r)
""").result_set

relationships = [
    {
        "source_internal_id": row[0],
        "target_internal_id": row[1],
        "type": row[2],
        "properties": row[3],
    }
    for row in rel_rows
]

if len(nodes) <= TARGET:
    print(f"Graph already has {len(nodes)} nodes. Nothing to delete.")
    raise SystemExit(0)

# Save all current nodes and relationships before any deletion.
backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup_path = backup_dir / f"veyra-before-prune-{stamp}.json"

with backup_path.open("w") as f:
    json.dump({
        "created_at": stamp,
        "graph": "VEYRA",
        "nodes": nodes,
        "relationships": relationships,
    }, f)

print(f"Backup saved: {backup_path}")
print(f"Nodes: {len(nodes)} | Relationships: {len(relationships)}")

# Keep every account, then prioritize useful investigation records.
priority = [
    "Report", "Case", "IncomingMessage", "Message",
    "Evidence", "Brand", "Domain", "URL", "ObservedDomain",
    "Scenario", "PaymentIdentifier", "Post", "Platform",
]

def rank(node):
    labels = set(node["labels"])
    if "Account" in labels:
        return (0, str(node["properties"].get("id", "")))
    for i, label in enumerate(priority, start=1):
        if label in labels:
            return (i, str(node["properties"].get("id", "")))
    return (len(priority) + 1, str(node["properties"].get("id", "")))

ordered = sorted(nodes, key=rank)
keep = ordered[:TARGET]
remove = ordered[TARGET:]
keep_ids = {n["internal_id"] for n in keep}

print(f"\nPlanned: keep {len(keep)} nodes; delete {len(remove)} nodes.")
print("Kept label counts:")
from collections import Counter
counts = Counter(label for n in keep for label in n["labels"])
for label, count in counts.most_common():
    print(f"  {label}: {count}")

print("\nWARNING: pruning to 550 total nodes may remove message/URL/report paths.")
print("Full pre-prune backup is saved above.")
confirm = input('Type DELETE-2600 (or the actual removal count shown above) to continue: ').strip()
expected = f"DELETE-{len(remove)}"
if confirm != expected:
    print("Cancelled. No nodes were deleted.")
    raise SystemExit(0)

remove_ids = [n["internal_id"] for n in remove]
for start in range(0, len(remove_ids), BATCH_SIZE):
    batch = remove_ids[start:start + BATCH_SIZE]
    graph.query("""
        MATCH (n)
        WHERE id(n) IN $ids
        DETACH DELETE n
    """, {"ids": batch})
    print(f"Deleted batch {start + len(batch)}/{len(remove_ids)}")

remaining = graph.query("MATCH (n) RETURN count(n)").result_set[0][0]
print(f"\nFinished. Remaining nodes: {remaining}")
print(f"Backup: {backup_path}")
