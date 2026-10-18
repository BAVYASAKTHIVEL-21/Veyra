from mcp.server.fastmcp import FastMCP
from agent.investigator import list_scenarios, investigate_scenario
from agent.memory_retriever import retrieve_investigations

mcp = FastMCP("Veyra Investigation Tools")


@mcp.tool()
def get_scenarios() -> dict:
    """List the available fictional Veyra investigation scenarios."""
    return {"scenarios": list_scenarios()}


@mcp.tool()
def investigate(scenario_id: str) -> dict:
    """Investigate a synthetic scenario using Veyra's FalkorDB graph."""
    return investigate_scenario(scenario_id)


@mcp.tool()
def get_previous_investigations(scenario_id: str) -> dict:
    """Retrieve previously saved investigation reports for a scenario."""
    reports = retrieve_investigations(scenario_id, limit=5)
    return {
        "scenario_id": scenario_id,
        "count": len(reports),
        "investigations": reports,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")


