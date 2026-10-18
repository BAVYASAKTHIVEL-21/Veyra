
from graph.connection import get_graph


def retrieve_conversations(
    session_id: str,
    limit: int = 10,
) -> list[dict]:
    """Retrieve recent conversation turns from a memory session."""

    graph = get_graph()

    result = graph.query(
        """
        MATCH (s:MemorySession {id: $session_id})-[:HAS_TURN]->(t:ConversationTurn)
        RETURN t.id, t.user_message, t.assistant_message, t.created_at
        ORDER BY t.created_at DESC
        LIMIT $limit
        """,
        {
            "session_id": session_id,
            "limit": max(1, min(limit, 50)),
        },
    )

    memories = []

    for row in result.result_set:
        memories.append({
            "id": row[0],
            "user_message": row[1],
            "assistant_message": row[2],
            "created_at": row[3],
        })

    return memories


def search_conversations(
    search_text: str,
    limit: int = 10,
) -> list[dict]:
    """Search saved conversations by a text fragment."""

    if not search_text.strip():
        return []

    graph = get_graph()

    result = graph.query(
        """
        MATCH (t:ConversationTurn)
        WHERE toLower(t.user_message) CONTAINS toLower($search_text)
           OR toLower(t.assistant_message) CONTAINS toLower($search_text)
        RETURN t.id, t.user_message, t.assistant_message, t.created_at
        ORDER BY t.created_at DESC
        LIMIT $limit
        """,
        {
            "search_text": search_text.strip(),
            "limit": max(1, min(limit, 50)),
        },
    )

    return [
        {
            "id": row[0],
            "user_message": row[1],
            "assistant_message": row[2],
            "created_at": row[3],
        }
        for row in result.result_set
    ]


def retrieve_investigations(
    scenario_id: str,
    limit: int = 10,
) -> list[dict]:
    """Retrieve saved investigation reports for a scenario."""

    import json

    from graph.connection import get_graph

    graph = get_graph()

    result = graph.query(
        """
        MATCH (s:Scenario {id: $scenario_id})
              -[:HAS_INVESTIGATION]->(i:Investigation)
        RETURN i.id, i.status, i.summary, i.report_json,
               i.created_at, i.updated_at
        ORDER BY i.created_at DESC
        LIMIT $limit
        """,
        {
            "scenario_id": scenario_id,
            "limit": max(1, min(limit, 50)),
        },
    )

    investigations = []

    for row in result.result_set:
        try:
            report = json.loads(row[3]) if row[3] else {}
        except (TypeError, json.JSONDecodeError):
            report = {}

        investigations.append({
            "investigation_id": row[0],
            "status": row[1],
            "summary": row[2],
            "created_at": row[4],
            "updated_at": row[5],
            "report": report,
        })

    return investigations



def retrieve_relevant_memories(
    search_text: str,
    limit: int = 5,
) -> list[dict]:
    """Search conversation memories across all sessions."""
    if not search_text.strip():
        return []

    graph = get_graph()

    result = graph.query(
        """
        MATCH (s:MemorySession)-[:HAS_TURN]->(t:ConversationTurn)
        WHERE toLower(t.user_message) CONTAINS toLower($search_text)
           OR toLower(t.assistant_message) CONTAINS toLower($search_text)
        RETURN s.id, t.id, t.user_message,
               t.assistant_message, t.created_at
        ORDER BY t.created_at DESC
        LIMIT $limit
        """,
        {
            "search_text": search_text.strip(),
            "limit": max(1, min(limit, 20)),
        },
    )

    return [
        {
            "session_id": row[0],
            "id": row[1],
            "user_message": row[2],
            "assistant_message": row[3],
            "created_at": row[4],
        }
        for row in result.result_set
    ]


def retrieve_recent_conversations(limit: int = 20) -> list[dict]:
    """Retrieve recent conversation turns across all sessions."""
    graph = get_graph()

    result = graph.query(
        """
        MATCH (s:MemorySession)-[:HAS_TURN]->(t:ConversationTurn)
        RETURN s.id, t.id, t.user_message,
               t.assistant_message, t.created_at
        ORDER BY t.created_at DESC
        LIMIT $limit
        """,
        {"limit": max(1, min(limit, 50))},
    )

    return [
        {
            "session_id": row[0],
            "id": row[1],
            "user_message": row[2],
            "assistant_message": row[3],
            "created_at": row[4],
        }
        for row in result.result_set
    ]
