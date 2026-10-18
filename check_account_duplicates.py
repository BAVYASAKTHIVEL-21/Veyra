from graph.connection import get_graph

graph = get_graph()

queries = {
    "Total graph nodes": """
        MATCH (n)
        RETURN count(n)
    """,
    "Account nodes": """
        MATCH (a:Account)
        RETURN count(a)
    """,
    "Duplicate account IDs": """
        MATCH (a:Account)
        WITH a.id AS account_id, count(*) AS total
        WHERE account_id IS NOT NULL AND total > 1
        RETURN account_id, total
        ORDER BY total DESC
        LIMIT 50
    """,
    "Accounts with duplicate usernames": """
        MATCH (a:Account)
        WITH a.username AS username, collect(a.id) AS ids
        WHERE username IS NOT NULL AND size(ids) > 1
        RETURN username, ids
        LIMIT 50
    """,
    "Account ID distribution": """
        MATCH (a:Account)
        RETURN a.id, a.username
        ORDER BY a.id
    """
}

for title, query in queries.items():
    print(f"\n--- {title} ---")
    try:
        rows = graph.query(query).result_set
        for row in rows:
            print(row)
    except Exception as e:
        print("Query error:", e)
