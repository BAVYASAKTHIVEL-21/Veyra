
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


from agent.memory_writer import save_conversation
from agent.memory_retriever import (
    retrieve_conversations,
    retrieve_relevant_memories,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)

SYSTEM_PROMPT = """
You are Veyra, an evidence intelligence assistant with persistent memory.

Use available MCP tools to retrieve facts before answering questions
about investigation scenarios.

You may receive previous conversation memories. Use them when relevant,
but distinguish saved conversation claims from verified evidence.
A previous AI answer is not independent evidence.

Rules:
- Never invent evidence, entities, or relationships.
- Distinguish observations from interpretations.
- Connections alone do not prove wrongdoing.
- Explain uncertainty and limitations.
- The dataset contains fictional synthetic scenarios only.
- If a memory is not available, do not pretend to remember it.
"""


async def ask_veyra(
    question: str,
    session_id: str | None = None,
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Check the project .env file."
        )

    # Direct CLI calls get their own session unless a session is supplied.
    session_id = session_id or str(uuid.uuid4())

    groq_client = Groq(api_key=api_key)

    # Retrieve the recent history for this conversation.
    memories = await asyncio.to_thread(
        retrieve_conversations,
        session_id,
        3,
    )

    
    # Search saved memories across sessions using useful terms
    # extracted from the user's question.
    question_terms = [
        term.strip(".,!?;:\"'()[]{}")
        for term in question.split()
        if len(term.strip(".,!?;:\"'()[]{}")) >= 4
    ]

    cross_session_memories = []
    seen_memory_ids = set()

    # Case assessments must stay focused on the current case.
    # Avoid injecting unrelated cross-session memories into their token budget.
    if not session_id.startswith("case-"):
        for term in question_terms[:5]:
            matches = await asyncio.to_thread(
                retrieve_relevant_memories,
                term,
                5,
            )

            for memory in matches:
                memory_id = memory.get("id")
                if memory_id and memory_id not in seen_memory_ids:
                    seen_memory_ids.add(memory_id)
                    cross_session_memories.append(memory)

    cross_session_memories = cross_session_memories[:3]

    
    memory_context = ""

    if memories:
        memory_context += (
            "\n\nPrevious conversation memories from this session "
            "(saved conversation claims, not verified evidence):\n"
            + json.dumps(
                memories,
                ensure_ascii=False,
                default=str,
            )[:2500]
        )

    if cross_session_memories:
        memory_context += (
            "\n\nRelevant memories from other sessions "
            "(saved conversation claims, not verified evidence):\n"
            + json.dumps(
                cross_session_memories,
                ensure_ascii=False,
                default=str,
            )[:1500]
        )


    server_params = StdioServerParameters(
        command=os.getenv("VEYRA_MCP_PYTHON", "/usr/local/bin/python"),
        args=[str(PROJECT_ROOT / "backend" / "mcp_server.py")],
        env={
            **os.environ,
            "PYTHONPATH": str(PROJECT_ROOT / "backend"),
        },
    )

    answer = ""

    async with stdio_client(server_params) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()
            tool_map = {tool.name: tool for tool in mcp_tools.tools}

            groq_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or tool.name,
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in mcp_tools.tools
            ]

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT + memory_context,
                },
                {"role": "user", "content": question},
            ]

            for _ in range(3):
                response = await asyncio.to_thread(
                    groq_client.chat.completions.create,
                    model=GROQ_MODEL,
                    messages=messages,
                    tools=groq_tools,
                    tool_choice="auto",
                    temperature=0.2,
                )

                message = response.choices[0].message
                messages.append(message.model_dump(exclude_none=True))

                if not message.tool_calls:
                    answer = message.content or ""
                    break

                for tool_call in message.tool_calls:
                    name = tool_call.function.name

                    if name not in tool_map:
                        result = {"error": f"Unknown MCP tool: {name}"}
                    else:
                        try:
                            arguments = json.loads(
                                tool_call.function.arguments or "{}"
                            )
                            tool_result = await session.call_tool(
                                name,
                                arguments=arguments,
                            )

                            # Bound tool output sent to Groq. This does not
                            # modify or delete the underlying FalkorDB evidence.
                            content_items = []
                            remaining_chars = 4000

                            for item in tool_result.content:
                                item_text = getattr(item, "text", None)
                                if item_text is None:
                                    continue

                                if remaining_chars <= 0:
                                    content_items.append({
                                        "type": "text",
                                        "text": "[Tool output truncated for context budget.]",
                                    })
                                    break

                                clipped_text = item_text[:remaining_chars]
                                content_items.append({
                                    "type": item.type,
                                    "text": clipped_text,
                                })
                                remaining_chars -= len(clipped_text)

                            result = {
                                "isError": tool_result.isError,
                                "content": content_items,
                            }
                        except Exception as exc:
                            result = {
                                "error": f"Tool execution failed: {exc}"
                            }

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, default=str),
                        }
                    )

            if not answer:
                # Final synthesis pass: use the evidence already returned by
                # MCP, and prevent another tool-call cycle.
                final_response = await asyncio.to_thread(
                    groq_client.chat.completions.create,
                    model=GROQ_MODEL,
                    messages=messages + [{
                        "role": "system",
                        "content": (
                            "Now provide your final answer using only the "
                            "tool results already present in this conversation. "
                            "Do not request more tools. If evidence is missing "
                            "or truncated, state that limitation explicitly."
                        ),
                    }],
                    tool_choice="none",
                    temperature=0.2,
                )
                answer = (
                    final_response.choices[0].message.content or
                    "I retrieved investigation data, but could not produce "
                    "a final summary. Please ask about a specific finding."
                )

    # Persist the completed conversation turn.
    await asyncio.to_thread(
        save_conversation,
        session_id,
        question,
        answer,
    )

    return answer


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()

    if not question:
        question = input("Ask Veyra: ").strip()

    if not question:
        print("Please enter a question.")
        raise SystemExit(1)

    try:
        answer = asyncio.run(ask_veyra(question))
        print("\nVeyra:", answer)
    except Exception:
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
