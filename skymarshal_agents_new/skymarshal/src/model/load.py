from langchain_aws import ChatBedrock

# Uses US cross-region inference profile for Claude Sonnet 4.5
# This provides optimal performance with multi-region availability in US
# https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def load_model() -> ChatBedrock:
    """
    Get Bedrock model client using US Sonnet 4.5 CRIS profile.
    Uses IAM authentication via the execution role.

    Returns:
        ChatBedrock: Configured model instance with structured output support
    """
    return ChatBedrock(
        model_id=MODEL_ID,
        model_kwargs={
            "temperature": 0.3,  # Lower temperature for more consistent structured output
            "max_tokens": 8192,  # Increased for Sonnet 4.5's larger context
        },
    )
