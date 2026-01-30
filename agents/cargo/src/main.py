from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

# System Prompt for Cargo Agent
SYSTEM_PROMPT = """You are the Cargo Agent - responsible for cargo operations and critical shipment management.

Your role is to:
1. Identify critical and time-sensitive cargo
2. Assess cargo offload requirements
3. Evaluate alternative cargo routing
4. Balance PAX vs cargo priorities
5. Minimize cargo revenue loss

Cargo Priority Classes:
- Priority 1: Live animals, human remains, dangerous goods
- Priority 2: Perishables (food, flowers, pharmaceuticals)
- Priority 3: High-value shipments, e-commerce
- Priority 4: General cargo

Offload Decision Criteria:
- Weight/balance requirements
- Time sensitivity
- Customer commitments (SLAs)
- Revenue impact
- Rerouting feasibility

Chain-of-Thought Analysis:
1. Parse cargo manifest
2. Identify critical shipments
3. Check time constraints
4. Evaluate offload impact
5. Find alternative routings
6. Calculate revenue loss
7. Recommend cargo strategy

Output format:
{
    "agent": "cargo",
    "cargo_summary": {
        "total_weight": "12,500 kg",
        "critical_shipments": 3,
        "perishables": 2,
        "revenue_at_risk": "$85,000"
    },
    "offload_recommendation": {
        "offload_required": false,
        "offload_candidates": [],
        "alternative_routing": ["options"]
    },
    "impact": {
        "sla_breaches": 0,
        "customer_impact": "LOW",
        "revenue_loss": "$0"
    },
    "recommendations": ["cargo strategy"],
    "reasoning": "cargo analysis"
}"""

# Define agent-specific function tool
@tool
def analyze_cargo_impact(input_data: str) -> str:
    """
    Cargo operations and critical shipment analyzer

    Args:
        input_data: JSON string containing disruption scenario and relevant data

    Returns:
        JSON string containing agent analysis and recommendations
    """
    # TODO: Implement cargo logic
    return f"Cargo analysis: {input_data}"

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()

# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Instantiate model
llm = load_model()

@app.entrypoint
async def invoke(payload):
    """
    Cargo Agent Entrypoint

    Processes disruption scenarios and provides business analysis
    """
    # Load MCP Tools
    tools = await mcp_client.get_tools()

    # Define the agent with cargo tools
    graph = create_agent(llm, tools=tools + [analyze_cargo_impact])

    # Process the user prompt
    prompt = payload.get("prompt", f"Analyze this disruption as cargo")

    # Include disruption data if provided
    disruption = payload.get("disruption", {})

    # Build context-aware message with system prompt
    message = f"""{SYSTEM_PROMPT}

---

USER REQUEST:
{prompt}

Disruption Data:
{disruption}

Provide analysis from the perspective of cargo (business).
"""

    # Run the agent
    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]})

    # Return result
    return {
        "agent": "cargo",
        "category": "business",
        "result": result["messages"][-1].content
    }

if __name__ == "__main__":
    # Run local development server on port 8080
    app.run()
