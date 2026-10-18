
import json
import uuid
from datetime import datetime, timezone

from graph.connection import get_graph


def _now():
    return datetime.now(timezone.utc).isoformat()



def save_conversation(
    session_id: str,
    user_message: str,
    assistant_message: str,
    turn_id: str | None = None,
) -> str:
    """Persist one conversation turn; repeated turn IDs are safe to retry."""

    graph = get_graph()
    turn_id = turn_id or str(uuid.uuid4())
    created_at = _now()

    graph.query(
        """
        MERGE (s:MemorySession {id: $session_id})
        ON CREATE SET s.created_at = $created_at
        SET s.updated_at = $created_at

        MERGE (t:ConversationTurn {id: $turn_id})
        ON CREATE SET
            t.user_message = $user_message,
            t.assistant_message = $assistant_message,
            t.created_at = $created_at

        MERGE (s)-[:HAS_TURN]->(t)
        """,
        {
            "session_id": session_id,
            "turn_id": turn_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "created_at": created_at,
        },
    )

    return turn_id


def save_investigation(report: dict) -> str:
    """Persist an investigation report and link it to its scenario."""
    import json

    from graph.connection import get_graph

    scenario = report.get("scenario") or {}
    scenario_id = scenario.get("id")
    investigation_id = report.get("investigation_id")

    if not scenario_id:
        raise ValueError("Investigation report has no scenario.id")
    if not investigation_id:
        raise ValueError("Investigation report has no investigation_id")

    saved_at = _now()
    graph = get_graph()

    graph.query(
        """
        MERGE (s:Scenario {id: $scenario_id})
        ON CREATE SET s.name = $scenario_name

        MERGE (i:Investigation {id: $investigation_id})
        ON CREATE SET i.created_at = $saved_at

        SET i.scenario_id = $scenario_id,
            i.status = $status,
            i.summary = $summary,
            i.report_json = $report_json,
            i.updated_at = $saved_at

        MERGE (s)-[:HAS_INVESTIGATION]->(i)
        """,
        {
            "scenario_id": scenario_id,
            "scenario_name": scenario.get("name", ""),
            "investigation_id": investigation_id,
            "status": report.get("status", "unknown"),
            "summary": report.get("summary", ""),
            "report_json": json.dumps(report, default=str),
            "saved_at": saved_at,
        },
    )

    return investigation_id
