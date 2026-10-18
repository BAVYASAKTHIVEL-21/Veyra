from graph.connection import get_graph

graph = get_graph()

queries = {
    "Account count": """
        MATCH (a:Account)
        RETURN count(a)
    """,
    "Accounts without relationships": """
        MATCH (a:Account)
        WHERE NOT (a)--()
        RETURN a.id, a.name
        LIMIT 100
    """,
    "Accounts with scenario links": """
        MATCH (a:Account)-[:IN_SCENARIO]-()
        RETURN count(DISTINCT a)
    """,
    "Accounts with report links": """
        MATCH (a:Account)-[:REPORTS_ACCOUNT|INVOLVES_ACCOUNT|SUPPORTED_BY]-()
        RETURN count(DISTINCT a)
    """,
    "Account properties sample": """
        MATCH (a:Account)
        RETURN a.id, a.name, a.username, a.account_type, a.is_synthetic
        LIMIT 20
    """,
}

for title, query in queries.items():
    print(f"\n--- {title} ---")
    try:
        result = graph.query(query)
        for row in result.result_set:
            print(row)
    except Exception as e:
        print("Query error:", e)
