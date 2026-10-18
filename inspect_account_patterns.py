from graph.connection import get_graph

graph = get_graph()

queries = {
    "Account ID ranges": """
        MATCH (a:Account)
        RETURN a.id
        ORDER BY a.id
        LIMIT 15
    """,
    "Synthetic account count": """
        MATCH (a:Account)
        WHERE a.is_synthetic = true
        RETURN count(a)
    """,
    "Accounts connected by relationship type": """
        MATCH (a:Account)-[r]-()
        RETURN type(r), count(r), count(DISTINCT a)
        ORDER BY count(r) DESC
    """,
    "Report-linked account samples": """
        MATCH (a:Account)-[r:REPORTS_ACCOUNT|INVOLVES_ACCOUNT|SUPPORTED_BY]-()
        RETURN a.id, a.username, type(r)
        LIMIT 30
    """,
    "Scenario and message node counts": """
        MATCH (n)
        WHERE any(label IN labels(n)
          WHERE label IN ['Scenario','Message','IncomingMessage','Case','Report','Evidence'])
        RETURN labels(n), count(n)
        ORDER BY labels(n)
    """
}

for title, query in queries.items():
    print(f"\n--- {title} ---")
    try:
        for row in graph.query(query).result_set:
            print(row)
    except Exception as e:
        print("Query error:", e)
