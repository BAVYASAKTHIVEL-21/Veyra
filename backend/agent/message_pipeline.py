import traceback
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from graph.connection import get_graph


def now():
    return datetime.now(timezone.utc).isoformat()


def extract_domains(message):
    """Extract hostnames observed in the submitted message."""
    urls = re.findall(r"https?://[^\s<>\"']+", message, flags=re.I)
    domains = set()

    for url in urls:
        try:
            host = (urlparse(url.rstrip(".,);]")).hostname or "").lower()
            if host:
                domains.add(host)
        except ValueError:
            continue

    return sorted(domains)


def analyze_message(message):
    """Fast initial checks. These are indicators, not a verdict."""
    domains = extract_domains(message)
    text = message.lower()

    indicators = []

    if domains:
        indicators.append({
            "type": "contains_link",
            "description": "The message contains one or more URLs.",
        })

    urgency_terms = (
        "immediately", "urgent", "suspended", "verify now",
        "send money", "arrest", "processing fee",
    )
    matched = [term for term in urgency_terms if term in text]

    if matched:
        indicators.append({
            "type": "urgency_or_pressure",
            "description": "The message contains pressure or urgency language.",
            "matched_terms": matched,
        })

    return {
        "indicators": indicators,
        "observed_domains": domains,
        "initial_status": "needs_review" if indicators else "received",
        "assessment": (
            "Potential warning indicators found. Investigate the evidence."
            if indicators
            else "No configured warning indicators detected. This does not "
                 "establish that the message is safe."
        ),
    }


def create_case(message, sender_account_id=None, source="user_submission"):
    """Create a case once, or reuse the matching persisted investigation."""
    import hashlib

    graph = get_graph()
    timestamp = now()
    initial = analyze_message(message)
    normalized = " ".join(message.split()).casefold()

    # Reuse matching legacy cases created before deduplication was added.
    existing_rows = graph.query(
        """
        MATCH (c:Entity:Case)-[:CONCERNS_MESSAGE]->
              (m:Entity:IncomingMessage)
        WHERE toLower(trim(m.text)) = toLower(trim($message))
        OPTIONAL MATCH (c)-[:INVOLVES_ACCOUNT]->(a:Entity:Account)
        WITH c, m, a
        WHERE
            ($sender_account_id IS NULL AND a.id IS NULL)
            OR a.id = $sender_account_id
        RETURN properties(c), m.id
        ORDER BY c.created_at DESC
        LIMIT 1
        """,
        {
            "message": message.strip(),
            "sender_account_id": sender_account_id,
        },
    ).result_set

    if existing_rows:
        props, message_id = existing_rows[0]
        return {
            "case_id": props["id"],
            "message_id": message_id,
            "status": props.get("status", "unknown"),
            "reused": True,
            "created": False,
            **initial,
        }

    # Stable IDs make simultaneous identical submissions converge on
    # the same case and message rather than generating fresh UUIDs.
    identity = normalized + "\n" + (sender_account_id or "")
    dedupe_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    case_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "veyra-case:" + dedupe_key))
    message_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "veyra-message:" + dedupe_key))
    creation_token = str(uuid.uuid4())

    case_rows = graph.query(
        """
        MERGE (c:Entity:Case {id: $case_id})
        ON CREATE SET
            c.status = 'investigating',
            c.source = $source,
            c.created_at = $timestamp,
            c.updated_at = $timestamp,
            c.initial_assessment = $assessment,
            c.findings_json = '[]',
            c.dedupe_key = $dedupe_key,
            c.creation_token = $creation_token
        RETURN properties(c)
        """,
        {
            "case_id": case_id,
            "source": source,
            "timestamp": timestamp,
            "assessment": initial["assessment"],
            "dedupe_key": dedupe_key,
            "creation_token": creation_token,
        },
    ).result_set

    if not case_rows:
        raise RuntimeError("FalkorDB did not return the created or reused case.")

    props = case_rows[0][0]
    created = props.get("creation_token") == creation_token

    # MERGE makes repeat writes to the same deterministic message idempotent.
    graph.query(
        """
        MERGE (m:Entity:IncomingMessage {id: $message_id})
        ON CREATE SET
            m.text = $message,
            m.created_at = $timestamp,
            m.source = $source
        WITH m
        MATCH (c:Entity:Case {id: $case_id})
        MERGE (c)-[:CONCERNS_MESSAGE]->(m)
        """,
        {
            "message_id": message_id,
            "message": message,
            "timestamp": timestamp,
            "source": source,
            "case_id": case_id,
        },
    )

    if sender_account_id:
        graph.query(
            """
            MATCH (c:Entity:Case {id: $case_id})
            MATCH (a:Entity:Account {id: $account_id})
            MERGE (c)-[:INVOLVES_ACCOUNT]->(a)
            """,
            {"case_id": case_id, "account_id": sender_account_id},
        )

    for domain in initial["observed_domains"]:
        domain_id = "observed-domain:" + domain
        graph.query(
            """
            MERGE (d:Entity:ObservedDomain {id: $domain_id})
            ON CREATE SET d.domain = $domain,
                          d.first_seen_at = $timestamp
            SET d.last_seen_at = $timestamp
            WITH d
            MATCH (m:Entity:IncomingMessage {id: $message_id})
            MERGE (m)-[:CONTAINS_LINK]->(d)
            """,
            {
                "domain_id": domain_id,
                "domain": domain,
                "timestamp": timestamp,
                "message_id": message_id,
            },
        )
        graph.query(
            """
            MATCH (c:Entity:Case {id: $case_id})
            MERGE (d:Entity:ObservedDomain {id: $domain_id})
            ON CREATE SET d.domain = $domain
            MERGE (c)-[:OBSERVED_DOMAIN]->(d)
            """,
            {"case_id": case_id, "domain_id": domain_id, "domain": domain},
        )

    return {
        "case_id": case_id,
        "message_id": message_id,
        "status": props.get("status", "investigating"),
        "reused": not created,
        "created": created,
        **initial,
    }




def record_query_event(case_id, event):
    """Persist truthful progress events without letting logging failures crash traversal."""
    import json
    from datetime import datetime, timezone

    event = {
        **event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Progress is diagnostic metadata. A transient write failure should not
    # abort the underlying graph traversal; the final case snapshot is saved
    # separately and remains authoritative.
    for attempt in range(2):
        try:
            graph = get_graph()
            rows = graph.query(
                """
                MATCH (c:Entity:Case {id: $case_id})
                RETURN c.progress_json
                LIMIT 1
                """,
                {"case_id": case_id},
            ).result_set

            if not rows:
                return

            raw = rows[0][0]
            try:
                events = json.loads(raw) if raw else []
            except (TypeError, ValueError):
                events = []

            events.append(event)
            events = events[-100:]

            graph.query(
                """
                MATCH (c:Entity:Case {id: $case_id})
                SET c.progress_json = $progress_json
                """,
                {
                    "case_id": case_id,
                    "progress_json": json.dumps(events, ensure_ascii=False),
                },
            )
            return
        except Exception as exc:
            if attempt == 0:
                print(
                    f"[VEYRA PROGRESS RETRY] case={case_id}: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
            else:
                print(
                    f"[VEYRA PROGRESS WRITE SKIPPED] case={case_id}: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

def investigate_case(case_id):
    """Investigate a case using its linked account and real graph paths."""
    import json
    from agent.graph_traversal import traverse_graph

    graph = get_graph()
    timestamp = now()

    try:
        case_rows = graph.query(
            """
            MATCH (c:Entity:Case {id: $case_id})
            OPTIONAL MATCH (c)-[:INVOLVES_ACCOUNT]->(a:Entity:Account)
            RETURN c.id, collect(DISTINCT a.id)
            """,
            {"case_id": case_id},
        ).result_set

        if not case_rows:
            return

        account_ids = case_rows[0][1] or []
        findings = []
        all_nodes = {}
        all_edges = {}

        # URL matching remains useful, but is not required:
        # investigate from every account explicitly linked to the case.
        start_ids = [str(value) for value in account_ids if value]

        # If the message contains URLs, also resolve them to existing graph
        # Domain nodes. Never create a graph node merely to claim a match.
        domain_rows = graph.query(
            """
            MATCH (c:Entity:Case {id: $case_id})
                  -[:OBSERVED_DOMAIN]->(o:Entity:ObservedDomain)
            RETURN DISTINCT coalesce(
                o.domain, o.name, o.hostname,
                replace(o.id, 'observed-domain:', '')
            )
            """,
            {"case_id": case_id},
        ).result_set

        for row in domain_rows:
            hostname = str(row[0] or "").strip().lower()
            if not hostname:
                continue

            matches = graph.query(
                """
                MATCH (d:Entity:Domain)
                WHERE toLower(trim(coalesce(
                    d.domain, d.name, d.hostname, d.url, ""
                ))) = $hostname
                RETURN d.id
                LIMIT 10
                """,
                {"hostname": hostname},
            ).result_set

            for match_row in matches:
                if match_row[0]:
                    start_ids.append(str(match_row[0]))

        # Keep the traversal bounded and deterministic.
        start_ids = list(dict.fromkeys(start_ids))

        for start_id in start_ids:
            record_query_event(case_id, {
                "stage": "traversal_started",
                "message": f"Starting multi-hop traversal from {start_id}",
                "start_id": start_id,
                "max_hops": None,
            })

            def emit_query_event(event):
                record_query_event(case_id, {
                    **event,
                    "start_id": start_id,
                })

            result = traverse_graph(
                start_id,
                max_hops=5,
                limit=None,
                progress_callback=emit_query_event,
            )

            record_query_event(case_id, {
                "stage": "traversal_completed",
                "message": (
                    f"Traversal from {start_id} returned "
                    f"{result.get('node_count', 0)} nodes and "
                    f"{result.get('edge_count', 0)} relationships."
                ),
                "start_id": start_id,
                "node_count": result.get("node_count", 0),
                "edge_count": result.get("edge_count", 0),
                "path_count": result.get("path_count", 0),
                "truncated": result.get("truncated", False),
            })

            for node in result.get("nodes", []):
                node_id = str(node.get("id") or "")
                if node_id:
                    all_nodes[node_id] = node

            for edge in result.get("edges", []):
                source_id = str(edge.get("from") or "")
                target_id = str(edge.get("to") or "")
                edge_type = str(edge.get("type") or "CONNECTED_TO")
                if source_id and target_id:
                    key = (source_id, edge_type, target_id)
                    all_edges[key] = edge

        # Store meaningful findings that the existing UI can use to request
        # traversals and display actual entities.
        for node_id, node in all_nodes.items():
            labels = node.get("labels") or []
            props = node.get("properties") or {}
            kind = next(
                (label for label in labels if label != "Entity"),
                "Entity",
            )
            if kind not in {
                "Account", "Report", "Evidence", "Domain",
                "ObservedDomain", "PaymentIdentifier", "PaymentHandle",
                "Scenario", "Post", "Brand", "URL",
            }:
                continue

            finding = {
                "entity_id": node_id,
                "entity_type": kind,
                "entity_name": (
                    props.get("name") or props.get("username")
                    or props.get("domain") or props.get("hostname")
                    or props.get("url") or props.get("id") or node_id
                ),
                "connected_account_id": (
                    node_id if kind == "Account" else None
                ),
                "report_id": node_id if kind == "Report" else None,
                "domain": (
                    props.get("domain") or props.get("hostname")
                    if kind in {"Domain", "ObservedDomain"} else None
                ),
                "payment_identifier_id": (
                    node_id if kind in {"PaymentIdentifier", "PaymentHandle"}
                    else None
                ),
                "scenario_id": node_id if kind == "Scenario" else None,
            }
            findings.append(finding)

        # Assess reports directly against the case's sender account IDs.
        # Do not rely only on graph traversal to discover report relationships.
        report_rows = []
        if account_ids:
            report_rows = graph.query(
                """
                MATCH (r:Entity:Report)-[:REPORTS_ACCOUNT]->(a:Entity:Account)
                WHERE a.id IN $account_ids
                OPTIONAL MATCH (r)-[:SUBMITTED_BY]->(p:Entity:Reporter)
                RETURN r.id, a.id, p.id, r.reason, r.status, r.is_synthetic
                ORDER BY r.id
                """,
                {"account_ids": [str(value) for value in account_ids if value]},
            ).result_set

        reports_by_id = {}
        independent_reporters = set()
        for row in report_rows:
            report_id, account_id, reporter_id, reason, report_status, is_synthetic = row
            if not report_id:
                continue

            report_id = str(report_id)
            reports_by_id[report_id] = {
                "report_id": report_id,
                "account_id": str(account_id) if account_id else None,
                "reporter_id": str(reporter_id) if reporter_id else None,
                "reason": str(reason) if reason else "Reason not recorded",
                "status": str(report_status) if report_status else "unknown",
                "is_synthetic": bool(is_synthetic),
            }
            if reporter_id:
                independent_reporters.add(str(reporter_id))

        # Enrich reports already discovered by graph traversal.
        # Traversal findings may initially contain only the report ID.
        existing_report_ids = set()
        for item in findings:
            report_id = item.get("report_id")
            if not report_id and item.get("entity_type") == "Report":
                report_id = item.get("entity_id")
            if not report_id:
                continue

            report_id = str(report_id)
            item["report_id"] = report_id
            existing_report_ids.add(report_id)

            report = reports_by_id.get(report_id)
            if report:
                item["entity_name"] = report["reason"]
                item["connected_account_id"] = report["account_id"]
                item["reporter_id"] = report["reporter_id"]
                item["report_status"] = report["status"]
                item["is_synthetic"] = report["is_synthetic"]
                item["reason"] = report["reason"]

        # Include reports even if graph traversal did not reach them.
        for report_id, report in reports_by_id.items():
            if report_id not in existing_report_ids:
                findings.append({
                    "entity_id": report_id,
                    "entity_type": "Report",
                    "entity_name": report["reason"],
                    "report_id": report_id,
                    "connected_account_id": report["account_id"],
                    "reporter_id": report["reporter_id"],
                    "report_status": report["status"],
                    "is_synthetic": report["is_synthetic"],
                    "reason": report["reason"],
                })

        report_count = len(reports_by_id)
        reporter_count = len(independent_reporters)
        corroborating_evidence = any(
            item.get("entity_type") in {
                "Evidence", "Domain", "URL", "PaymentIdentifier",
                "PaymentHandle", "Brand"
            }
            for item in findings
        )

        if reporter_count >= 2 and corroborating_evidence:
            assessment = (
                f"High risk: {report_count} linked report(s) from "
                f"{reporter_count} distinct reporter(s), with additional "
                "corroborating graph evidence. Treat this account as a "
                "potential scam; verify the evidence before making a final decision."
            )
        elif reporter_count >= 2:
            assessment = (
                f"High caution: {report_count} linked report(s) from "
                f"{reporter_count} distinct reporter(s). The account may be "
                "associated with spam. Review each report and its status."
            )
        elif reporter_count == 1:
            assessment = (
                f"Caution: {report_count} linked report(s) from one known "
                "reporter. This may indicate spam, but it is not proof that "
                "the account is fake."
            )
        elif report_count:
            assessment = (
                f"Caution: {report_count} linked report(s) were found, but "
                "reporter identity is missing, so independent reports cannot "
                "be counted reliably."
            )
        elif findings and not any(
            item.get("entity_type") in {
                "Evidence", "Domain", "ObservedDomain", "URL",
                "PaymentIdentifier", "PaymentHandle", "Brand", "Report"
            }
            for item in findings
        ):
            assessment = (
                "This message looks normal based on the available evidence. "
                "No linked reports or obvious suspicious indicators were found "
                "in the connected graph. This is not a guarantee that the "
                "sender or message is safe."
            )
        elif findings:
            assessment = (
                "Review recommended: connected graph evidence was found, "
                "but no reports linked to this sender were found. "
                "Check the message, links, and evidence before deciding."
            )
        else:
            assessment = (
                "No linked reports or matching connected graph evidence were "
                "found. This does not establish that the message or account is safe."
            )

        status = "needs_review" if findings or report_count else "completed"

        snapshot = {
            "nodes": list(all_nodes.values()),
            "edges": list(all_edges.values()),
            "start_account_ids": start_ids,
            "truncated": False,
            "source": "FalkorDB traverse_graph",
            "captured_at": timestamp,
        }

        graph.query(
            """
            MATCH (c:Entity:Case {id: $case_id})
            SET c.status = $status,
                c.findings_json = $findings_json,
                c.graph_snapshot_json = $graph_snapshot_json,
                c.updated_at = $timestamp,
                c.investigation_completed_at = $timestamp,
                c.assessment = $assessment
            REMOVE c.error
            """,
            {
                "case_id": case_id,
                "status": status,
                "findings_json": json.dumps(findings, ensure_ascii=False),
                "graph_snapshot_json": json.dumps(snapshot, ensure_ascii=False),
                "timestamp": timestamp,
                "assessment": assessment,
            },
        )

        print(
            f"[VEYRA INVESTIGATION] case={case_id} "
            f"starts={len(start_ids)} nodes={len(all_nodes)} "
            f"edges={len(all_edges)} findings={len(findings)}",
            flush=True,
        )

    except Exception as exc:
        traceback.print_exc()
        error_message = f"{type(exc).__name__}: {exc}"[:500]

        print(
            f"[VEYRA INVESTIGATION FAILED] case={case_id}: {error_message}",
            flush=True,
        )

        # Use a fresh graph connection to record the failure.
        try:
            recovery_graph = get_graph()
            recovery_graph.query(
                """
                MATCH (c:Entity:Case {id: $case_id})
                SET c.status = 'investigation_failed',
                    c.error = $error,
                    c.updated_at = $timestamp
                """,
                {
                    "case_id": case_id,
                    "error": error_message,
                    "timestamp": now(),
                },
            )
        except Exception as recovery_exc:
            print(
                f"[VEYRA ERROR RECORDING FAILED] case={case_id}: "
                f"{type(recovery_exc).__name__}: {recovery_exc}",
                flush=True,
            )


def get_case(case_id):
    graph = get_graph()

    rows = graph.query(
        """
        MATCH (c:Entity:Case {id: $case_id})
        RETURN properties(c)
        """,
        {"case_id": case_id},
    ).result_set

    if not rows:
        return None

    import json

    result = rows[0][0]
    result["findings"] = json.loads(result.pop("findings_json", "[]"))
    snapshot_raw = result.pop("graph_snapshot_json", None)
    progress_raw = result.pop("progress_json", None)
    try:
        result["graph_snapshot"] = json.loads(snapshot_raw) if snapshot_raw else None
    except (TypeError, ValueError):
        result["graph_snapshot"] = None
    try:
        result["progress_events"] = json.loads(progress_raw) if progress_raw else []
    except (TypeError, ValueError):
        result["progress_events"] = []
    return result



def list_cases(limit=200):
    """Return persisted investigation cases with lightweight archive metadata."""
    import json

    graph = get_graph()
    safe_limit = max(1, min(int(limit), 500))

    # Do not retrieve large graph snapshots for every row in the archive.
    rows = graph.query(
        """
        MATCH (c:Entity:Case)
        RETURN
            c.id AS id,
            c.investigation_id AS investigation_id,
            c.sender AS sender,
            c.message AS message,
            c.status AS status,
            c.classification AS classification,
            c.risk_level AS risk_level,
            c.agent_risk_level AS agent_risk_level,
            c.risk AS risk,
            c.confidence AS confidence,
            c.assessment AS assessment,
            c.agent_reply AS agent_reply,
            c.agent_assessments_json AS agent_assessments_json,
            c.created_at AS created_at,
            c.updated_at AS updated_at,
            c.investigation_completed_at AS investigation_completed_at,
            c.error AS error
        LIMIT $limit
        """,
        {"limit": safe_limit},
    ).result_set

    cases = []
    for row in rows:
        case = dict(zip(
            [
                "id", "investigation_id", "sender", "message", "status",
                "classification", "risk_level", "agent_risk_level", "risk",
                "confidence", "assessment", "agent_reply", "agent_assessments_json", "created_at", "updated_at",
                "investigation_completed_at", "error"
            ],
            row
        ))
        cases.append(case)

    return cases
