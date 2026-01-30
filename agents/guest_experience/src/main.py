from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

# System Prompt for Guest Experience Agent
SYSTEM_PROMPT = """You are the Guest Experience Agent - responsible for passenger satisfaction and service recovery.

Your role is to:
1. Assess passenger impact and inconvenience
2. Calculate appropriate compensation (EU261, airline policy)
3. Recommend service recovery actions
4. Optimize for customer satisfaction and loyalty
5. Minimize reputational damage

Passenger Segments to consider:
- Premium cabin (First, Business)
- Frequent flyers (Gold, Platinum status)
- Special needs (PRM, UMNR)
- Group bookings
- Connecting passengers

EU261 Compensation (for EU flights):
- < 1500km: €250 (>3hr delay)
- 1500-3500km: €400 (>3hr delay)
- > 3500km: €600 (>4hr delay)

Service Recovery Options:
- Meal vouchers
- Hotel accommodation
- Lounge access
- Rebooking flexibility
- Compensation (cash/miles)
- Upgrade offers

Chain-of-Thought Analysis:
1. Parse passenger manifest and segments
2. Calculate delay duration
3. Determine EU261 eligibility
4. Assess passenger inconvenience levels
5. Calculate compensation amounts
6. Recommend service recovery actions
7. Estimate satisfaction impact

Output format:
{
    "agent": "guest_experience",
    "passenger_impact": {
        "total_affected": 615,
        "premium_cabin": 48,
        "elite_status": 127,
        "special_needs": 8
    },
    "compensation_required": {
        "eu261_eligible": 615,
        "amount_per_pax": "€400",
        "total_cost": "€246,000"
    },
    "service_recovery": [
        "Meal vouchers for all PAX",
        "Hotel accommodation for 87 connecting PAX",
        "Lounge access for premium cabin"
    ],
    "satisfaction_risk": "HIGH|MEDIUM|LOW",
    "recommendations": ["optimal service recovery"],
    "reasoning": "guest experience analysis"
}"""

# Define agent-specific function tool
@tool
def analyze_guest_impact(input_data: str) -> str:
    """
    Passenger satisfaction and compensation analyzer

    Args:
        input_data: JSON string containing disruption scenario and relevant data

    Returns:
        JSON string containing agent analysis and recommendations
    """
    # TODO: Implement guest_experience logic
    return f"Guest Experience analysis: {input_data}"

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()

# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Instantiate model
llm = load_model()

@app.entrypoint
async def invoke(payload):
    """
    Guest Experience Agent Entrypoint

    Processes disruption scenarios and provides business analysis
    """
    # Load MCP Tools
    tools = await mcp_client.get_tools()

    # Define the agent with guest_experience tools
    graph = create_agent(llm, tools=tools + [analyze_guest_impact])

    # Process the user prompt
    prompt = payload.get("prompt", f"Analyze this disruption as guest experience")

    # Include disruption data if provided
    disruption = payload.get("disruption", {})

    # Build context-aware message with system prompt
    message = f"""{SYSTEM_PROMPT}

---

USER REQUEST:
{prompt}

Disruption Data:
{disruption}

Provide analysis from the perspective of guest experience (business).
"""

    # Run the agent
    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]})

    # Return result
    return {
        "agent": "guest_experience",
        "category": "business",
        "result": result["messages"][-1].content
    }

if __name__ == "__main__":
    # Run local development server on port 8080
    app.run()
