from graph.connection import get_graph

graph = get_graph()

before = graph.query("""
    MATCH ()-[r]->()
    RETURN count(r)
""").result_set[0][0]

scenarios = graph.query("""
    MATCH ()-[r:IN_SCENARIO]->()
    RETURN count(r)
""").result_set[0][0]

print("Total edges before:", before)
print("IN_SCENARIO edges to delete:", scenarios)

if scenarios:
    graph.query("""
        MATCH ()-[r:IN_SCENARIO]->()
        DELETE r
    """)

after = graph.query("""
    MATCH ()-[r]->()
    RETURN count(r)
""").result_set[0][0]

print("Total edges after:", after)
print("Edges removed:", before - after)

for rel in [
    "FOLLOWS",
    "FRIENDS_WITH",
    "REPORTS_ACCOUNT",
    "SENDS_MESSAGE",
    "SENT_TO",
    "CONTAINS_LINK",
    "SHARES_DOMAIN",
    "SUPPORTED_BY",
]:
    result = graph.query(
        "MATCH ()-[r]->() WHERE type(r) = $rel RETURN count(r)",
        {"rel": rel},
    )
    print(f"{rel}: {result.result_set[0][0]}")
