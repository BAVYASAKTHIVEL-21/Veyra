import json
from pathlib import Path
from datetime import datetime, timezone
from graph.connection import get_graph

graph = get_graph()
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup = Path("backups")
backup.mkdir(exist_ok=True)

result = graph.query("""
    MATCH (a)-[r]->(b)
    RETURN a.id AS source, labels(a) AS source_labels,
           type(r) AS relationship,
           b.id AS target, labels(b) AS target_labels,
           properties(r) AS properties
""")

records = [
    {
        "source": row[0],
        "source_labels": row[1],
        "relationship": row[2],
        "target": row[3],
        "target_labels": row[4],
        "properties": row[5] or {},
    }
    for row in result.result_set
]

path = backup / f"veyra-before-social-cleanup-{stamp}.json"
path.write_text(json.dumps(records, indent=2, default=str))
print("Backup:", path)
print("Total edges:", len(records))

for rel in ("FOLLOWS", "FRIENDS_WITH", "IN_SCENARIO", "SHARES_DOMAIN"):
    count = sum(x["relationship"] == rel for x in records)
    print(f"{rel}: {count}")

print("\nNo database changes made.")
