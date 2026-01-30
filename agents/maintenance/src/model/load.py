from langchain_aws import ChatBedrock

# Model configuration for this agent
MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

def load_model() -> ChatBedrock:
    """
    Get Bedrock model client.
    Uses IAM authentication via the execution role.

    Model: global.anthropic.claude-sonnet-4-5-20250929-v1:0
    Provider: AWS Bedrock
    """
    return ChatBedrock(
        model_id=MODEL_ID,
        model_kwargs={
            "max_tokens": 4096,
            "temperature": 0.3,  # Lower for consistent analysis
        }
    )
