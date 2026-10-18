from graph.connection import get_graph

graph = get_graph()

print("\n=== GRAPH SIZE ===")
for query in [
    "MATCH (n) RETURN count(n)",
    "MATCH ()-[r]->() RETURN count(r)",
]:
    result = graph.query(query)
    print(result.result_set[0][0])

print("\n=== RELATIONSHIP COUNTS ===")
result = graph.query("""
    MATCH ()-[r]->()
    RETURN type(r) AS relationship, count(r) AS total
    ORDER BY total DESC
""")
for row in result.result_set:
    print(f"{row[0]}: {row[1]}")

print("\n=== NODE LABEL COUNTS ===")
result = graph.query("""
    MATCH (n)
    UNWIND labels(n) AS label
    RETURN label, count(*) AS total
    ORDER BY total DESC
""")
for row in result.result_set:
    print(f"{row[0]}: {row[1]}")
