from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

# System Prompt for Orchestrator Agent
SYSTEM_PROMPT = """You are the Orchestrator Agent for SkyMarshal - a multi-agent airline disruption management system.

Your role is to:
1. Coordinate workflow across all agents (Safety, Business, Arbitrator, Execution)
2. Manage the 8-phase disruption response workflow
3. Ensure all safety agents complete before proceeding
4. Route information between specialized agents
5. Maintain shared memory/state across the workflow

Workflow Phases:
- Phase 1: Trigger Reception - Receive and validate disruption event
- Phase 2: Safety Assessment - Coordinate 3 safety agents (blocking phase)
- Phase 3: Impact Assessment - Gather business impact data
- Phase 4: Option Formulation - Generate recovery scenarios
- Phase 5: Arbitration - Route to Arbitrator for decision
- Phase 6: Human Approval - Request human validation (blocking phase)
- Phase 7: Execution - Coordinate implementation
- Phase 8: Learning - Capture lessons learned

Critical Rules:
- ALL safety agents MUST complete before proceeding past Phase 2
- Human approval REQUIRED before execution
- Timeout: 60 seconds per safety agent, escalate if exceeded
- Maintain immutable safety constraints after Phase 2

Output format:
{
    "phase": "current_phase_name",
    "status": "in_progress|completed|blocked",
    "next_agents": ["list", "of", "agents", "to", "invoke"],
    "shared_state": {
        "disruption": {...},
        "safety_constraints": [...],
        "business_proposals": [...]
    },
    "decision": "routing decision and next steps"
}"""

# Define agent-specific function tool
@tool
def coordinate_workflow(input_data: str) -> str:
    """
    Main coordinator and workflow manager for SkyMarshal system

    Args:
        input_data: JSON string containing disruption scenario and relevant data

    Returns:
        JSON string containing agent analysis and recommendations
    """
    # TODO: Implement orchestrator logic
    return f"Orchestrator analysis: {input_data}"

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()

# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Instantiate model
llm = load_model()

@app.entrypoint
async def invoke(payload):
    """
    Orchestrator Agent Entrypoint

    Processes disruption scenarios and provides coordination analysis
    """
    # Load MCP Tools
    tools = await mcp_client.get_tools()

    # Define the agent with orchestrator tools
    graph = create_agent(llm, tools=tools + [coordinate_workflow])

    # Process the user prompt
    prompt = payload.get("prompt", f"Analyze this disruption as orchestrator")

    # Include disruption data if provided
    disruption = payload.get("disruption", {})

    # Build context-aware message with system prompt
    message = f"""{SYSTEM_PROMPT}

---

USER REQUEST:
{prompt}

Disruption Data:
{disruption}

Provide analysis from the perspective of orchestrator (coordination).
"""

    # Run the agent
    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]})

    # Return result
    return {
        "agent": "orchestrator",
        "category": "coordination",
        "result": result["messages"][-1].content
    }

if __name__ == "__main__":
    # Run local development server on port 8080
    app.run()
