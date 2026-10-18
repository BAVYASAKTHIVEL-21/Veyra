from datetime import datetime

from graph.connection import get_graph


def _relationship_id(relationship):
    return (relationship.get("properties") or {}).get("id")


def _edge_key(source, target, relationship):
    """Deduplicate the same displayed relationship without changing the DB."""
    endpoints = tuple(sorted((str(source), str(target))))
    properties = relationship.get("properties") or {}
    return (
        endpoints,
        relationship.get("type", "RELATED_TO"),
        _relationship_id(relationship),
        repr(properties),
    )


def _path_identity(node_ids, relationships):
    relationship_keys = [
        (
            rel.get("type"),
            _relationship_id(rel),
            repr(rel.get("properties") or {}),
        )
        for rel in relationships
    ]
    forward = (tuple(node_ids), tuple(relationship_keys))
    reverse = (
        tuple(reversed(node_ids)),
        tuple(reversed(relationship_keys)),
    )
    return min(forward, reverse, key=repr)


def traverse_graph(
    start_id: str,
    max_hops: int | None = None,
    limit: int | None = None,
    progress_callback=None,
):
    """Explore direct social connections and recursively follow threat evidence."""

    if not start_id or not start_id.strip():
        raise ValueError("start_id must not be empty")
    if max_hops is not None and max_hops < 1:
        raise ValueError("max_hops must be None or at least 1")
    if limit is not None and limit < 1:
        raise ValueError("limit must be None or at least 1")

    graph = get_graph()
    start_id = str(start_id).strip()

    def emit(event):
        if progress_callback:
            progress_callback(event)

    def node_record(node_id, labels, props):
        return {
            "id": str(node_id),
            "labels": labels or ["Entity"],
            "properties": props or {"id": str(node_id)},
        }

    def make_edge_key(source, target, rel_type, props):
        props = props or {}
        if rel_type == "FRIENDS_WITH":
            return (rel_type, *sorted((str(source), str(target))))
        return (
            str(source), rel_type or "RELATED_TO",
            str(target), repr(props),
        )

    expandable = {
        "REPORTS_ACCOUNT", "SHARES_DOMAIN",
        "SUPPORTED_BY", "OBSERVED_DOMAIN", "CONCERNS_MESSAGE",
        "CONTAINS_LINK", "INVOLVES_ACCOUNT", "PUBLISHED",
        "USES_PAYMENT", "POSSIBLE_IMPERSONATION_OF",
        "REFERENCES_BRAND", "MATCHES_CONTENT",
        "SENT_TO", "SENDS_MESSAGE",
    }

    start_query = """
        MATCH (s:Entity {id: $start_id})
        RETURN s.id, labels(s), properties(s)
        LIMIT 1
    """
    rows = graph.query(start_query, {"start_id": start_id}).result_set

    if not rows:
        return {
            "start_id": start_id, "max_hops": max_hops,
            "nodes": [], "edges": [], "paths": [],
            "node_count": 0, "edge_count": 0,
            "path_count": 0, "truncated": False,
        }

    row = rows[0]
    nodes = {start_id: node_record(row[0], row[1], row[2])}
    edges = {}
    visited = {start_id}
    frontier = {start_id}
    truncated = False

    query = """
        MATCH (s:Entity)-[r]-(m:Entity)
        WHERE s.id IN $frontier_ids
          AND m.id IS NOT NULL
          AND m.id <> s.id
          AND (
              $hop = 1
              OR type(r) IN $expandable_relationships
          )
        RETURN
          s.id, labels(s), properties(s),
          type(r), properties(r),
          m.id, labels(m), properties(m),
          startNode(r).id, endNode(r).id
    """

    hop = 0
    while frontier and (max_hops is None or hop < max_hops):
        hop += 1
        if not frontier:
            break

        frontier_ids = sorted(frontier)
        emit({
            "stage": "query_started",
            "message": f"Expanding hop {hop} from {len(frontier_ids)} nodes",
            "query": query,
            "parameters": {"frontier_ids": frontier_ids},
            "hop": hop,
        })

        try:
            rows = graph.query(
                query,
                {
                    "frontier_ids": frontier_ids,
                    "hop": hop,
                    "expandable_relationships": sorted(expandable),
                },
            ).result_set
        except Exception as exc:
            print(
                f"[VEYRA GRAPH QUERY FAILED] "
                f"start_id={start_id} hop={hop} "
                f"frontier_size={len(frontier_ids)} "
                f"error={type(exc).__name__}: {exc}",
                flush=True,
            )
            emit({
                "stage": "query_failed",
                "message": f"Hop {hop} failed: {type(exc).__name__}: {exc}",
                "query": query,
                "hop": hop,
            })
            raise

        next_frontier = set()
        hop_nodes = {}
        hop_edges = {}

        for row in rows:
            (
                source, source_labels, source_props,
                rel_type, rel_props,
                target, target_labels, target_props,
                actual_from, actual_to,
            ) = row

            if source is None or target is None:
                continue

            source, target = str(source), str(target)
            rel_type = rel_type or "RELATED_TO"
            # Scenario membership is not evidence and is hidden from cases.
            # Social relationships remain visible as context, but do not by
            # themselves cause further traversal or indicate suspiciousness.
            if rel_type == "IN_SCENARIO":
                continue
            rel_props = rel_props or {}

            for node_id, labels, props in (
                (source, source_labels, source_props),
                (target, target_labels, target_props),
            ):
                record = node_record(node_id, labels, props)
                nodes[node_id] = record
                hop_nodes[node_id] = record

            edge_from = str(actual_from or source)
            edge_to = str(actual_to or target)
            key = make_edge_key(edge_from, edge_to, rel_type, rel_props)

            edge = {
                "from": edge_from,
                "type": rel_type,
                "to": edge_to,
                "properties": rel_props,
            }
            edges.setdefault(key, edge)
            hop_edges.setdefault(key, edge)

            # Expand according to node role, not just relationship type.
            # This prevents a shared domain or message from triggering a
            # crawl through every unrelated account in the graph.
            source_labels = set(source_labels or [])
            target_labels = set(target_labels or [])

            source_is_account = "Account" in source_labels
            source_is_message = "Message" in source_labels
            source_is_domain = "Domain" in source_labels
            target_is_account = "Account" in target_labels

            account_evidence_edges = {
                "REPORTS_ACCOUNT",
                "SENDS_MESSAGE",
                "SENT_TO",
                "CONTAINS_LINK",
                "SHARES_DOMAIN",
                "USES_PAYMENT",
                "POSSIBLE_IMPERSONATION_OF",
                "SUPPORTED_BY",
                "INVOLVES_ACCOUNT",
            }

            message_evidence_edges = {
                "CONCERNS_MESSAGE",
                "CONTAINS_LINK",
                "OBSERVED_DOMAIN",
                "SUPPORTED_BY",
                "SHARES_DOMAIN",
                "USES_PAYMENT",
                "POSSIBLE_IMPERSONATION_OF",
                "REFERENCES_BRAND",
                "MATCHES_CONTENT",
            }

            domain_evidence_edges = {
                "SHARES_DOMAIN",
                "OBSERVED_DOMAIN",
                "SUPPORTED_BY",
                "CONTAINS_LINK",
                "POSSIBLE_IMPERSONATION_OF",
                "REFERENCES_BRAND",
            }

            should_expand = (
                (
                    source_is_account
                    and rel_type in account_evidence_edges
                    and not (
                        target_is_account
                        and rel_type != "REPORTS_ACCOUNT"
                    )
                )
                or (
                    source_is_message
                    and rel_type in message_evidence_edges
                    and not target_is_account
                )
                or (
                    source_is_domain
                    and rel_type in domain_evidence_edges
                    and not target_is_account
                )
                or (
                    rel_type in {
                        "REPORTS_ACCOUNT",
                        "SUPPORTED_BY",
                        "POSSIBLE_IMPERSONATION_OF",
                        "REFERENCES_BRAND",
                        "MATCHES_CONTENT",
                        "USES_PAYMENT",
                        "OBSERVED_DOMAIN",
                    }
                    and not target_is_account
                )
            )

            if should_expand and target not in visited:
                next_frontier.add(target)

        visited.update(next_frontier)

        emit({
            "stage": "hop_results",
            "hop": hop,
            "message": (
                f"Hop {hop}: {len(hop_nodes)} nodes, "
                f"{len(hop_edges)} unique relationships"
            ),
            "nodes": list(hop_nodes.values()),
            "edges": list(hop_edges.values()),
            "node_count": len(hop_nodes),
            "edge_count": len(hop_edges),
        })

        frontier = next_frontier

    # Preserve all discovered nodes and edges. 'limit' bounds paths only.
    paths = [
        {
            "start_id": start_id,
            "end_id": node_id,
            "hops": 1,
            "node_ids": [start_id, node_id],
            "relationships": [],
        }
        for node_id in sorted(visited)
        if node_id != start_id
    ]

    if limit is not None and len(paths) > limit:
        paths = paths[:limit]
        truncated = True

    selected_edges = sorted(
        edges.values(),
        key=lambda e: (e["from"], e["type"], e["to"]),
    )
    selected_nodes = [nodes[node_id] for node_id in sorted(nodes)]

    return {
        "start_id": start_id,
        "max_hops": max_hops,
        "nodes": selected_nodes,
        "edges": selected_edges,
        "paths": paths,
        "node_count": len(selected_nodes),
        "edge_count": len(selected_edges),
        "path_count": len(paths),
        "truncated": truncated,
    }
