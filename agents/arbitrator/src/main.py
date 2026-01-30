from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
from langchain_aws.retrievers import AmazonKnowledgeBasesRetriever

from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model
import boto3
import json

# Knowledge Base Configuration
KNOWLEDGE_BASE_ID = "UDONMVCXEW"
AWS_REGION = "us-east-1"
retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=KNOWLEDGE_BASE_ID,
    retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 10}},
)

# Initialize Bedrock Agent Runtime client
#bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)

# Define knowledge base retrieval tool
@tool
def query_skymarshal_knowledge(query: str) -> str:
    """
    Query the SkyMarshal Arbitrator Knowledge Base for aviation regulations,
    disruption management procedures, and decision-making guidelines.

    Args:
        query: The question or topic to search in the knowledge base

    Returns:
        Retrieved information from the knowledge base
    """
    try:
        results = retriever.invoke(query)
        # response = bedrock_agent_runtime.retrieve(
        #     knowledgeBaseId=KNOWLEDGE_BASE_ID,
        #     retrievalQuery={
        #         'text': query
        #     },
        #     retrievalConfiguration={
        #         'vectorSearchConfiguration': {
        #             'numberOfResults': 5
        #         }
        #     }
        # )

        # Extract and format the results
        # results = []
        # for result in response.get('retrievalResults', []):
        #     content = result.get('content', {}).get('text', '')
        #     score = result.get('score', 0)
        #     results.append(f"[Score: {score:.2f}] {content}")

        if results:
            return results
        else:
            return "No relevant information found in the knowledge base."

    except Exception as e:
        return f"Error querying knowledge base: {str(e)}"

# Define a simple function tool
@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers"""
    return a+b

# Import AgentCore Gateway as Streamable HTTP MCP Client
#try:
#    mcp_client = get_streamable_http_mcp_client()
#except Exception as e:
#    print(f"Warning: Could not initialize MCP client: {e}")
#    mcp_client = None

# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Instantiate model
llm = load_model()

@app.entrypoint
async def invoke(payload):
    """
    Entrypoint for the arbitrator agent.

    Handles multiple payload formats:
    - String: direct prompt
    - Dict with "prompt" key: {"prompt": "user input"}
    - None: uses default prompt
    """
    try:
        # Handle different payload formats
        if payload is None:
            prompt = "What is Agentic AI?"
        elif isinstance(payload, str):
            prompt = payload
        elif isinstance(payload, dict):
            prompt = payload.get("prompt", "What is Agentic AI?")
        else:
            prompt = str(payload)

        # Load MCP Tools (with error handling)
        tools = []
        #if mcp_client is not None:
        #    try:
        #        tools = await mcp_client.get_tools()
        #    except Exception as e:
        #        print(f"Warning: Could not load MCP tools: {e}")
        #       tools = []

        # Define the agent with knowledge base tool
        arbitrator = create_agent(llm, tools=tools + [add_numbers, query_skymarshal_knowledge])
    
        # Run the agent
        result = await arbitrator.ainvoke({"messages": [HumanMessage(content=prompt)]})

        # Return result
        return {
            "result": result["messages"][-1].content
        }

    except Exception as e:
        return {
            "error": str(e),
            "result": f"Error processing request: {str(e)}"
        }

if __name__ == "__main__":
    app.run()