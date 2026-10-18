from graph.connection import get_graph

graph = get_graph()

queries = {
    "All node labels": """
        MATCH (n)
        UNWIND labels(n) AS label
        RETURN label, count(*) AS total
        ORDER BY total DESC
    """,
    "Report records": """
        MATCH (r:Report)
        RETURN properties(r)
        LIMIT 30
    """,
    "Domain records": """
        MATCH (d:Domain)
        RETURN properties(d)
        LIMIT 30
    """,
    "Brand records": """
        MATCH (b:Brand)
        RETURN properties(b)
        LIMIT 20
    """,
    "URL-like records": """
        MATCH (n)
        WHERE any(k IN keys(n)
          WHERE toLower(k) CONTAINS 'url'
             OR toLower(k) CONTAINS 'link')
        RETURN labels(n), properties(n)
        LIMIT 30
    """,
    "Existing evidence relationships": """
        MATCH (a)-[r]->(b)
        WHERE type(r) IN [
          'REPORTS_ACCOUNT', 'POSSIBLE_IMPERSONATION_OF',
          'SUPPORTED_BY', 'REFERENCES_BRAND',
          'MATCHES_CONTENT', 'CONCERNS_MESSAGE',
          'CONTAINS_LINK', 'OBSERVED_DOMAIN'
        ]
        RETURN a.id, labels(a), type(r), b.id, labels(b), properties(r)
        LIMIT 100
    """
}

for title, query in queries.items():
    print(f"\n--- {title} ---")
    try:
        for row in graph.query(query).result_set:
            print(row)
    except Exception as e:
        print("Query error:", e)
