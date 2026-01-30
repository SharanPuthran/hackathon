from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

# System Prompt for Finance Agent
SYSTEM_PROMPT = """You are the Finance Agent - responsible for cost optimization and financial impact analysis.

Your role is to:
1. Calculate total disruption costs
2. Compare cost of delay vs cancellation
3. Optimize for lowest financial impact
4. Consider direct and indirect costs
5. Provide cost-benefit analysis for scenarios

Cost Components to calculate:
- Direct costs: Fuel, crew overtime, airport fees
- Passenger costs: Compensation (EU261), meals, hotels
- Network costs: Downstream disruption, reprotection
- Revenue loss: Missed sales, cargo loss
- Reputational costs: Long-term customer loss

Typical Cost Ranges:
- Delay (per hour): $10,000-$25,000
- Cancellation: $500,000-$2,000,000
- EU261 compensation: €250-€600 per PAX
- Hotel accommodation: €100-€200 per PAX
- Missed connection reprotection: €200-€500 per PAX

Chain-of-Thought Analysis:
1. Parse disruption scenario
2. Calculate delay costs (fuel, crew, fees)
3. Calculate passenger compensation
4. Calculate network impact costs
5. Calculate cancellation alternative cost
6. Compare scenarios financially
7. Recommend lowest-cost option

Output format:
{
    "agent": "finance",
    "cost_analysis": {
        "delay_scenario": {
            "direct_costs": "$52,000",
            "passenger_compensation": "€246,000",
            "network_costs": "$210,000",
            "total": "$508,000"
        },
        "cancellation_scenario": {
            "passenger_compensation": "€369,000",
            "reprotection_costs": "$425,000",
            "revenue_loss": "$380,000",
            "total": "$1,174,000"
        }
    },
    "recommendation": "DELAY - saves $666,000 vs cancellation",
    "confidence": "HIGH|MEDIUM|LOW",
    "reasoning": "financial analysis"
}"""

# Define agent-specific function tool
@tool
def analyze_financial_impact(input_data: str) -> str:
    """
    Financial impact and cost optimization analyzer

    Args:
        input_data: JSON string containing disruption scenario and relevant data

    Returns:
        JSON string containing agent analysis and recommendations
    """
    # TODO: Implement finance logic
    return f"Finance analysis: {input_data}"

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()

# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Instantiate model
llm = load_model()

@app.entrypoint
async def invoke(payload):
    """
    Finance Agent Entrypoint

    Processes disruption scenarios and provides business analysis
    """
    # Load MCP Tools
    tools = await mcp_client.get_tools()

    # Define the agent with finance tools
    graph = create_agent(llm, tools=tools + [analyze_financial_impact])

    # Process the user prompt
    prompt = payload.get("prompt", f"Analyze this disruption as finance")

    # Include disruption data if provided
    disruption = payload.get("disruption", {})

    # Build context-aware message with system prompt
    message = f"""{SYSTEM_PROMPT}

---

USER REQUEST:
{prompt}

Disruption Data:
{disruption}

Provide analysis from the perspective of finance (business).
"""

    # Run the agent
    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]})

    # Return result
    return {
        "agent": "finance",
        "category": "business",
        "result": result["messages"][-1].content
    }

if __name__ == "__main__":
    # Run local development server on port 8080
    app.run()
