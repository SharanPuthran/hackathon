from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

# System Prompt for Execution Agent
SYSTEM_PROMPT = """You are the Execution Agent - responsible for coordinating implementation of approved decisions.

Your role is to:
1. Break down decisions into executable tasks
2. Coordinate with operational teams
3. Monitor execution progress
4. Handle exceptions and blockers
5. Ensure smooth implementation

Execution Domains:
- Operations Control Center (OCC)
- Maintenance Operations
- Ground Operations
- Crew Scheduling
- Customer Service
- Network Control

Task Categories:
- Aircraft: Maintenance actions, aircraft swaps
- Crew: Crew assignments, rest periods
- Passengers: Rebooking, compensation, service
- Network: Schedule updates, slot coordination
- Regulatory: Notifications, approvals

Chain-of-Thought Analysis:
1. Parse arbitrator decision
2. Break into executable tasks
3. Assign tasks to responsible teams
4. Set execution timeline
5. Monitor progress
6. Handle exceptions
7. Confirm completion

Output format:
{
    "agent": "execution",
    "execution_plan": {
        "decision_id": "DEC-20260130-001",
        "scenario": "RS-001 Expedited Repair & Delay",
        "tasks": [
            {
                "task_id": "T001",
                "description": "Dispatch maintenance crew for hydraulic repair",
                "owner": "Maintenance Operations",
                "deadline": "ISO 8601",
                "status": "in_progress|completed|blocked"
            }
        ]
    },
    "timeline": {
        "start": "ISO 8601",
        "estimated_completion": "ISO 8601",
        "actual_completion": "ISO 8601 or null"
    },
    "status": "executing|completed|blocked",
    "exceptions": ["any blockers or issues"],
    "recommendations": ["execution optimizations"]
}"""

# Define agent-specific function tool
@tool
def coordinate_execution(input_data: str) -> str:
    """
    Execution coordinator and implementation manager

    Args:
        input_data: JSON string containing disruption scenario and relevant data

    Returns:
        JSON string containing agent analysis and recommendations
    """
    # TODO: Implement execution logic
    return f"Execution analysis: {input_data}"

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()

# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Instantiate model
llm = load_model()

@app.entrypoint
async def invoke(payload):
    """
    Execution Agent Entrypoint

    Processes disruption scenarios and provides coordination analysis
    """
    # Load MCP Tools
    tools = await mcp_client.get_tools()

    # Define the agent with execution tools
    graph = create_agent(llm, tools=tools + [coordinate_execution])

    # Process the user prompt
    prompt = payload.get("prompt", f"Analyze this disruption as execution")

    # Include disruption data if provided
    disruption = payload.get("disruption", {})

    # Build context-aware message with system prompt
    message = f"""{SYSTEM_PROMPT}

---

USER REQUEST:
{prompt}

Disruption Data:
{disruption}

Provide analysis from the perspective of execution (coordination).
"""

    # Run the agent
    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]})

    # Return result
    return {
        "agent": "execution",
        "category": "coordination",
        "result": result["messages"][-1].content
    }

if __name__ == "__main__":
    # Run local development server on port 8080
    app.run()
