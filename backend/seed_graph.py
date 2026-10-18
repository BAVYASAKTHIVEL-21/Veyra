import json
import os
import re
import sys
from pathlib import Path

# Allow importing backend/graph/connection.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph.connection import get_graph

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "synthetic_scenarios.json"

COLLECTIONS = {
    "platforms": "Platform",
    "scenarios": "Scenario",
    "accounts": "Account",
    "domains": "Domain",
    "brands": "Brand",
    "payment_identifiers": "PaymentIdentifier",
    "posts": "Post",
    "messages": "Message",
    "evidence": "Evidence",
    "reports": "Report",
}


def safe_properties(item):
    """Convert JSON values into graph-compatible properties."""
    props = {}
    for key, value in item.items():
        if key == "id" or value is None:
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        props[key] = value
    return props


def main():
    with DATA_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    if not data.get("is_synthetic"):
        raise ValueError("Refusing to load a dataset not marked synthetic.")

    graph = get_graph()
    known_ids = set()
    node_count = 0

    # Create or update nodes. Stable IDs make repeated runs idempotent.
    for collection, label in COLLECTIONS.items():
        for item in data.get(collection, []):
            entity_id = item.get("id")
            if not entity_id:
                raise ValueError(f"Missing ID in {collection}: {item}")

            if entity_id in known_ids:
                raise ValueError(f"Duplicate entity ID: {entity_id}")
            known_ids.add(entity_id)

            props = safe_properties(item)
            props["id"] = entity_id
            props["entity_type"] = label

            graph.query(
                f"MERGE (n:Entity:{label} {{id: $id}}) "
                "SET n += $props",
                {"id": entity_id, "props": props},
            )
            node_count += 1

    # Validate all endpoints before writing relationships.
    relationships = data.get("relationships", [])
    relationship_ids = set()
    for rel in relationships:
        rid = rel.get("id")
        if not rid or rid in relationship_ids:
            raise ValueError(f"Missing or duplicate relationship ID: {rid}")
        relationship_ids.add(rid)

        if rel.get("from") not in known_ids or rel.get("to") not in known_ids:
            raise ValueError(f"Unknown endpoint in relationship: {rel}")

        rel_type = rel.get("type", "")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", rel_type):
            raise ValueError(f"Invalid relationship type: {rel_type}")

    # Create or update edges. Relationship IDs prevent duplicate edges
    # when the loader is rerun.
    for rel in relationships:
        rel_type = rel["type"]
        rel_props = {
            key: value
            for key, value in rel.items()
            if key not in {"id", "from", "to", "type"} and value is not None
        }
        rel_props["id"] = rel["id"]

        graph.query(
            f"MATCH (a:Entity {{id: $from_id}}), "
            "(b:Entity {id: $to_id}) "
            f"MERGE (a)-[r:{rel_type} {{id: $rel_id}}]->(b) "
            "SET r += $props",
            {
                "from_id": rel["from"],
                "to_id": rel["to"],
                "rel_id": rel["id"],
                "props": safe_properties(rel_props),
            },
        )

    print("Veyra graph load completed!")
    print(f"Nodes processed: {node_count}")
    print(f"Relationships processed: {len(relationships)}")
    print(f"Graph: {os.getenv('FALKORDB_GRAPH', 'VEYRA')}")
    print("Dataset:", data.get("dataset_name", DATA_FILE.name))


if __name__ == "__main__":
    main()
