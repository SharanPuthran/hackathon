"""
SkyMarshal Arbitrator Agent - AgentCore Runtime Deployment
Built with AWS Bedrock AgentCore + LangGraph
Model: Claude Opus 4.5

This file wraps the existing LangGraph arbitrator agent for deployment
to AWS Bedrock AgentCore Runtime.

Usage:
    # Local testing
    python3 agentcore_arbitrator.py

    # Deploy to AgentCore Runtime
    agentcore configure -e agentcore_arbitrator.py
    agentcore deploy

    # Invoke deployed agent
    python3 test_agentcore_deployment.py
"""

from bedrock_agentcore import BedrockAgentCoreApp
from agents.arbitrator_agent import create_arbitrator_agent
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AgentCore app
app = BedrockAgentCoreApp()

# Create the arbitrator agent (LangGraph implementation)
arbitrator = create_arbitrator_agent()

@app.entrypoint
def invoke_arbitrator(payload: dict) -> dict:
    """
    AgentCore entrypoint for the SkyMarshal Arbitrator Agent.

    This function receives payloads from AgentCore Runtime and processes
    them through the LangGraph-based arbitrator workflow.

    Args:
        payload: Dictionary containing:
            - disruption_scenario: Flight disruption details
            - safety_assessments: Safety agent outputs
            - business_proposals: Business agent outputs
            - prompt (optional): Simple text prompt for testing

    Returns:
        Dictionary with:
            - decision: Selected recovery scenario
            - rationale: Detailed decision explanation
            - confidence_score: Confidence percentage (0-100)
            - scenarios_evaluated: List of all evaluated scenarios
    """

    logger.info("=" * 60)
    logger.info("AgentCore Arbitrator Agent Invoked")
    logger.info("=" * 60)

    try:
        # Handle simple prompt for testing
        if "prompt" in payload and not all(k in payload for k in ["disruption_scenario", "safety_assessments", "business_proposals"]):
            logger.info(f"Test prompt received: {payload.get('prompt')}")
            return {
                "status": "test_response",
                "message": "SkyMarshal Arbitrator Agent is running on AgentCore Runtime",
                "prompt_received": payload.get("prompt"),
                "capabilities": [
                    "Multi-criteria disruption analysis",
                    "Safety compliance verification",
                    "Business impact evaluation",
                    "Scenario ranking and decision-making"
                ]
            }

        # Extract inputs
        disruption = payload.get("disruption_scenario", {})
        safety = payload.get("safety_assessments", {})
        business = payload.get("business_proposals", {})

        logger.info(f"Processing disruption: {disruption.get('flight_number', 'Unknown')}")

        # Validate inputs
        if not disruption:
            raise ValueError("disruption_scenario is required")
        if not safety:
            raise ValueError("safety_assessments is required")
        if not business:
            raise ValueError("business_proposals is required")

        # Invoke the LangGraph arbitrator agent
        logger.info("Invoking LangGraph arbitrator workflow...")
        result = arbitrator.invoke(
            disruption_scenario=disruption,
            safety_assessments=safety,
            business_proposals=business
        )

        # Extract decision details
        decision = result.get("decision", {})
        rationale = result.get("rationale", "")
        confidence = result.get("confidence_score", 0)
        scenarios = result.get("scenarios_evaluated", [])

        logger.info(f"✅ Decision Made: {decision.get('scenario', 'Unknown')}")
        logger.info(f"   Confidence: {confidence}%")

        # Format response for AgentCore
        response = {
            "status": "success",
            "agent": result.get("agent", "arbitrator"),
            "model": result.get("model", "claude-opus-4-5"),
            "decision": decision,
            "rationale": rationale,
            "confidence_score": confidence,
            "scenarios_evaluated": scenarios,
            "disruption_context": {
                "flight_number": disruption.get("flight_number"),
                "route": disruption.get("route"),
                "issue": disruption.get("issue")
            },
            "timestamp": result.get("timestamp", "")
        }

        logger.info("=" * 60)
        return response

    except Exception as e:
        logger.error(f"❌ Error in arbitrator: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }


# Note: Healthcheck removed - may not be supported in this AgentCore version
# The entrypoint function handles all requests including health checks


if __name__ == "__main__":
    """
    Run the agent locally for testing.

    This starts a local HTTP server on port 8080 that mimics
    the AgentCore Runtime environment.
    """
    print("=" * 60)
    print("SkyMarshal Arbitrator Agent - AgentCore Runtime")
    print("=" * 60)
    print("Starting local development server on http://localhost:8080")
    print()
    print("Test with:")
    print("  curl -X POST http://localhost:8080/invoke \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"prompt\": \"Hello\"}'")
    print()
    print("Deploy to AWS:")
    print("  agentcore configure -e agentcore_arbitrator.py")
    print("  agentcore deploy")
    print("=" * 60)

    app.run()
