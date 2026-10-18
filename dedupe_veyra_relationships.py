import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from graph.connection import get_graph

graph = get_graph()
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

print("Reading all relationships...")
result = graph.query("""
    MATCH (a)-[r]->(b)
    RETURN id(r) AS rid,
           type(r) AS rel_type,
           a.id AS source_id,
           labels(a) AS source_labels,
           b.id AS target_id,
           labels(b) AS target_labels,
           properties(r) AS props
""")

relationships = []
for row in result.result_set:
    rid, rel_type, source_id, source_labels, target_id, target_labels, props = row
    relationships.append({
        "rid": rid,
        "type": rel_type,
        "source_id": source_id,
        "source_labels": source_labels,
        "target_id": target_id,
        "target_labels": target_labels,
        "properties": props or {},
    })

snapshot_path = backup_dir / f"veyra-relationships-before-dedupe-{stamp}.json"
snapshot_path.write_text(json.dumps(relationships, indent=2, default=str))
print(f"Saved {len(relationships)} relationships to {snapshot_path}")

# Only consider exact duplicates: same type, endpoints AND properties.
groups = defaultdict(list)
for rel in relationships:
    key = (
        rel["type"],
        rel["source_id"],
        rel["target_id"],
        json.dumps(rel["properties"], sort_keys=True, default=str),
    )
    groups[key].append(rel)

duplicate_ids = []
duplicate_records = []

for group in groups.values():
    if len(group) > 1:
        # Keep one relationship; remove only additional identical copies.
        group.sort(key=lambda r: r["rid"])
        for duplicate in group[1:]:
            duplicate_ids.append(duplicate["rid"])
            duplicate_records.append(duplicate)

report_path = backup_dir / f"veyra-duplicate-relationships-{stamp}.json"
report_path.write_text(json.dumps(duplicate_records, indent=2, default=str))

print(f"Exact duplicate relationships found: {len(duplicate_ids)}")
print(f"Duplicate report saved to {report_path}")

if not duplicate_ids:
    print("No exact duplicate relationships found. Nothing deleted.")
    raise SystemExit(0)

# Delete in small batches; nodes and non-identical edges are untouched.
deleted = 0
for start in range(0, len(duplicate_ids), 100):
    batch = duplicate_ids[start:start + 100]
    result = graph.query("""
        MATCH ()-[r]->()
        WHERE id(r) IN $ids
        DELETE r
        RETURN count(*) AS deleted
    """, {"ids": batch})
    if result.result_set:
        deleted += result.result_set[0][0]

print(f"Deleted duplicate relationships: {deleted}")

remaining = graph.query("MATCH ()-[r]->() RETURN count(r)")
print(f"Relationships remaining: {remaining.result_set[0][0]}")
print("Done. No nodes were deleted.")
