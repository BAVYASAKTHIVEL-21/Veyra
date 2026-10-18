import uuid

from graph.connection import get_graph
from agent.memory_writer import save_investigation
from agent.graph_traversal import traverse_graph


def _rows(query, params=None):
    result = get_graph().query(query, params or {})
    return result.result_set


def list_scenarios():
    rows = _rows("""
        MATCH (s:Entity:Scenario)
        RETURN s.id, s.name, s.description, s.expected_outcome
        ORDER BY s.id
    """)

    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "expected_outcome": row[3],
        }
        for row in rows
    ]


def investigate_scenario(scenario_id: str, max_hops: int = 3):
    scenarios = list_scenarios()
    scenario = next(
        (item for item in scenarios if item["id"] == scenario_id),
        None,
    )

    if scenario is None:
        return {"error": "Scenario not found", "scenario_id": scenario_id}

    node_rows = _rows("""
        MATCH (n:Entity)-[:IN_SCENARIO]->
              (s:Entity:Scenario {id: $sid})
        RETURN n.id, labels(n), properties(n)
        ORDER BY n.id
    """, {"sid": scenario_id})

    scenario_nodes = [
        {"id": row[0], "labels": row[1], "properties": row[2]}
        for row in node_rows
    ]

    if not scenario_nodes:
        return {
            "scenario": scenario,
            "status": "no_entities_found",
            "nodes": [],
            "edges": [],
            "paths": [],
            "observations": [],
            "limitations": ["No entities are linked to this scenario."],
        }

    # Include all scenario nodes and their relationships.
    scenario_ids = [node["id"] for node in scenario_nodes]

    edge_rows = _rows("""
        MATCH (a:Entity)-[r]->(b:Entity)
        WHERE a.id IN $ids AND b.id IN $ids
        RETURN a.id, type(r), b.id, properties(r)
        ORDER BY a.id, type(r), b.id
    """, {"ids": scenario_ids})

    edges_by_key = {}
    for row in edge_rows:
        edge = {
            "from": row[0],
            "type": row[1],
            "to": row[2],
            "properties": row[3],
        }
        relationship_id = (edge.get("properties") or {}).get("id")
        key = (
            edge["from"],
            edge["type"],
            edge["to"],
            relationship_id,
            repr(edge.get("properties") or {}),
        )
        edges_by_key[key] = edge

    nodes_by_id = {node["id"]: node for node in scenario_nodes}
    paths = []
    traversal_truncated = False

    # Traverse outward from each account in the scenario.
    account_ids = [
        node["id"]
        for node in scenario_nodes
        if "Account" in node["labels"]
    ]

    for account_id in account_ids:
        remaining_paths = max(0, 100 - len(paths))

        if remaining_paths == 0:
            traversal_truncated = True
            break

        traversal = traverse_graph(
            account_id,
            max_hops=max_hops,
            limit=remaining_paths,
        )

        traversal_truncated = (
            traversal_truncated or traversal["truncated"]
        )

        for node in traversal["nodes"]:
            nodes_by_id.setdefault(node["id"], node)

        for edge in traversal["edges"]:
            relationship_id = (edge.get("properties") or {}).get("id")
            key = (
                edge["from"],
                edge["type"],
                edge["to"],
                relationship_id,
                repr(edge.get("properties") or {}),
            )
            edges_by_key.setdefault(key, edge)

        paths.extend(traversal["paths"])

    nodes = sorted(nodes_by_id.values(), key=lambda node: node["id"])
    edges = sorted(
        edges_by_key.values(),
        key=lambda edge: (edge["from"], edge["type"], edge["to"]),
    )

    observation_types = {
        "SHARES_DOMAIN",
        "MATCHES_CONTENT",
        "USES_PAYMENT",
        "SHARES_PAYMENT",
        "POSSIBLE_IMPERSONATION_OF",
        "REPORTS_ACCOUNT",
        "SUPPORTED_BY",
        "PUBLISHED",
    }

    observations = [
        {
            "type": edge["type"],
            "from": edge["from"],
            "to": edge["to"],
            "statement": (
                f"The graph records {edge['type']} between "
                f"{edge['from']} and {edge['to']}."
            ),
            "interpretation": (
                "This is a graph observation, not proof of wrongdoing."
            ),
        }
        for edge in edges
        if edge["type"] in observation_types
    ]

    evidence_count = sum(
        "Evidence" in node["labels"] for node in nodes
    )

    report = {
        "investigation_id": f"{scenario_id}-{uuid.uuid4().hex}",
        "scenario": scenario,
        "status": "completed",
        "summary": (
            f"Retrieved {len(nodes)} unique entities and "
            f"{len(edges)} unique relationships for "
            f"{scenario['name']}, with multi-hop traversal."
        ),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "evidence_count": evidence_count,
        "nodes": nodes,
        "edges": edges,
        "paths": paths,
        "path_count": len(paths),
        "max_hops": max_hops,
        "traversal_truncated": traversal_truncated,
        "observations": observations,
        "assessment": (
            "Review the paths and supporting evidence before drawing "
            "a conclusion. Shared infrastructure or relationships alone "
            "do not establish intent or wrongdoing."
        ),
        "limitations": [
            "Traversal follows relationships in either direction.",
            "The path limit may mean some connections were not returned."
            if traversal_truncated
            else "Traversal did not reach its configured path limit.",
            "The graph contains synthetic demonstration data.",
            "Connections alone do not establish intent or wrongdoing.",
        ],
    }

    save_investigation(report)
    return report