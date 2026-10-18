from graph.connection import get_graph

graph = get_graph()

labels = ["Account", "Domain", "Message", "Report", "Reporter"]

for label in labels:
    result = graph.query(
        f"MATCH (n:Entity:{label}) "
        "WHERE n.id STARTS WITH 'demo_' "
        "RETURN n.id"
    )

    for row in result.result_set:
        old_id = row[0]
        new_id = old_id[len("demo_"):]

        graph.query(
            f"MATCH (n:Entity:{label} {{id: $old_id}}) "
            "SET n.id = $new_id",
            {"old_id": old_id, "new_id": new_id},
        )
        print(f"{label}: {old_id} -> {new_id}")

# Rename internal relationship IDs too.
result = graph.query(
    "MATCH ()-[r]->() "
    "WHERE r.id STARTS WITH 'demo_' "
    "RETURN r.id"
)

for row in result.result_set:
    old_id = row[0]
    new_id = old_id[len("demo_"):]

    graph.query(
        "MATCH ()-[r]->() "
        "WHERE r.id = $old_id "
        "SET r.id = $new_id",
        {"old_id": old_id, "new_id": new_id},
    )

print("Migration completed.")
