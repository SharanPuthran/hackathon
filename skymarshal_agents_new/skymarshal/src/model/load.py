import logging
from typing import Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from langchain_aws import ChatBedrock

logger = logging.getLogger(__name__)

# Configure boto3 with increased timeouts for long-running model invocations
# Claude models can take 60+ seconds for complex reasoning tasks
# Using eu-west-1 for Bedrock endpoints (lower latency from Europe)
BEDROCK_REGION = "eu-west-1"

BOTO_CONFIG = Config(
    region_name=BEDROCK_REGION,
    read_timeout=180,  # 3 minutes - allows for complex multi-step reasoning
    connect_timeout=10,  # 10 seconds for connection
    retries={'max_attempts': 3, 'mode': 'adaptive'}  # Retry on transient failures
)

# Model priority list (will try in order until one works)
# Priority: Performance > Cost > Availability
# Using GLOBAL cross-region inference profiles for better availability and reduced throttling
MODEL_PRIORITY = [
    {
        "id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "name": "Claude Sonnet 4.5 (Global CRIS)",
        "temperature": 0.3,
        "max_tokens": 8192,
        "reason": "Global cross-region inference - optimal balance of speed, accuracy, and availability"
    },
    {
        "id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "name": "Claude Haiku 4.5 (Global CRIS)",
        "temperature": 0.3,
        "max_tokens": 8192,
        "reason": "Global cross-region inference - fast and cost-effective"
    },
    {
        "id": "global.anthropic.claude-opus-4-5-20251101-v1:0",
        "name": "Claude Opus 4.5 (Global CRIS)",
        "temperature": 0.3,
        "max_tokens": 8192,
        "reason": "Global cross-region inference - most powerful reasoning"
    },
    {
        "id": "global.amazon.nova-2-lite-v1:0",
        "name": "Amazon Nova 2 Lite (Global CRIS)",
        "temperature": 0.3,
        "max_tokens": 8192,
        "reason": "Global cross-region inference - cost-effective fallback"
    },
    {
        "id": "us.amazon.nova-premier-v1:0",
        "name": "Amazon Nova Premier (US)",
        "temperature": 0.3,
        "max_tokens": 8192,
        "reason": "US regional fallback - Amazon's flagship model"
    }
]

# Cache for tested models to avoid repeated checks
_tested_models = {}

# Agent-specific model configuration
# Safety agents use Sonnet 4.5 for accuracy-critical analysis
# Business agents use Haiku 4.5 for speed and cost optimization
# Arbitrator uses Sonnet 4.5 for complex conflict resolution
AGENT_MODEL_CONFIG = {
    "safety": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "temperature": 0.3,
        "max_tokens": 8192,
        "reason": "Safety-critical analysis requires high accuracy"
    },
    "business": {
        "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "temperature": 0.3,
        "max_tokens": 4096,
        "reason": "Business analysis prioritizes speed over deep reasoning"
    },
    "arbitrator": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "temperature": 0.2,
        "max_tokens": 8192,
        "reason": "Conflict resolution requires balanced reasoning"
    }
}


def _test_model(model_id: str) -> bool:
    """
    Test if a model is available and not throttled by making a minimal test call.
    
    Args:
        model_id: The model ID to test
        
    Returns:
        bool: True if model is available and working, False otherwise
    """
    # Check cache first
    if model_id in _tested_models:
        return _tested_models[model_id]
    
    try:
        logger.info(f"Testing model availability: {model_id}")
        
        # Create a minimal test client
        test_client = ChatBedrock(
            model_id=model_id,
            region_name=BEDROCK_REGION,
            model_kwargs={
                "temperature": 0.1,
                "max_tokens": 10,  # Minimal tokens for test
            },
        )
        
        # Make a minimal test call
        test_client.invoke("test")
        
        logger.info(f"✅ Model {model_id} is available and working")
        _tested_models[model_id] = True
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = str(e)
        
        if 'ThrottlingException' in error_message or 'Too many tokens' in error_message:
            logger.warning(f"⚠️ Model {model_id} is throttled (quota exceeded)")
        elif 'ValidationException' in error_message or 'not found' in error_message.lower():
            logger.warning(f"⚠️ Model {model_id} is not available in this region")
        else:
            logger.warning(f"⚠️ Model {model_id} test failed: {error_message}")
        
        _tested_models[model_id] = False
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ Model {model_id} test failed with unexpected error: {e}")
        _tested_models[model_id] = False
        return False


def load_model(skip_test: bool = True) -> ChatBedrock:
    """
    Get Bedrock model client with intelligent fallback.
    
    Tries models in priority order:
    1. Claude Sonnet 4.5 Global CRIS (best performance + availability)
    2. Claude Haiku 4.5 Global CRIS (fast and cost-effective)
    3. Claude Opus 4.5 Global CRIS (most powerful)
    4. Amazon Nova 2 Lite Global CRIS (cost-effective fallback)
    5. Amazon Nova Premier US (regional fallback)
    
    Args:
        skip_test: If True, skip model availability test for faster startup (default: True)
                   Global CRIS endpoints are highly available, so testing is usually unnecessary.
    
    Returns:
        ChatBedrock: Configured model instance with structured output support
        
    Raises:
        RuntimeError: If no models are available
    """
    logger.info("Loading model...")
    
    for model_config in MODEL_PRIORITY:
        model_id = model_config["id"]
        model_name = model_config["name"]
        
        # Skip test for faster startup when using Global CRIS endpoints
        if skip_test:
            logger.info(f"✅ Using {model_name} in {BEDROCK_REGION} (skip_test=True): {model_config['reason']}")
            return ChatBedrock(
                model_id=model_id,
                region_name=BEDROCK_REGION,
                model_kwargs={
                    "temperature": model_config["temperature"],
                    "max_tokens": model_config["max_tokens"],
                },
                config=BOTO_CONFIG  # Use increased timeout configuration
            )
        
        logger.info(f"Trying {model_name} ({model_id})...")
        
        # Test if model is available
        if _test_model(model_id):
            logger.info(f"✅ Using {model_name} in {BEDROCK_REGION}: {model_config['reason']}")
            
            return ChatBedrock(
                model_id=model_id,
                region_name=BEDROCK_REGION,
                model_kwargs={
                    "temperature": model_config["temperature"],
                    "max_tokens": model_config["max_tokens"],
                },
                config=BOTO_CONFIG  # Use increased timeout configuration
            )
        else:
            logger.warning(f"❌ {model_name} not available, trying next model...")
    
    # If we get here, no models worked
    error_msg = "❌ CRITICAL: No models available! All models failed or are throttled."
    logger.error(error_msg)
    logger.error("Available models tried:")
    for model_config in MODEL_PRIORITY:
        logger.error(f"  - {model_config['name']}: {model_config['id']}")
    
    raise RuntimeError(
        "No Bedrock models available. Please check:\n"
        "1. AWS credentials and permissions\n"
        "2. Model access in AWS Bedrock console\n"
        "3. Daily token quotas (may need to wait or request increase)\n"
        "4. Region availability (us-east-1 recommended)"
    )


def load_fast_model() -> ChatBedrock:
    """
    Get fast Bedrock model for business agents (Haiku 4.5).
    
    Uses Claude Haiku 4.5 Global CRIS for faster response times.
    Ideal for business agents where speed is prioritized over deep reasoning.
    
    Returns:
        ChatBedrock: Fast model instance optimized for speed
    """
    logger.info(f"Loading fast model (Claude Haiku 4.5 Global CRIS) in {BEDROCK_REGION}...")
    
    return ChatBedrock(
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        region_name=BEDROCK_REGION,
        model_kwargs={
            "temperature": 0.3,
            "max_tokens": 4096,  # Reduced for faster responses
        },
        config=BOTO_CONFIG
    )


def load_arbitrator_model() -> ChatBedrock:
    """
    Get powerful Bedrock model for arbitrator (Sonnet 4.5 or Opus 4.5).
    
    Uses Claude Sonnet 4.5 Global CRIS for optimal reasoning capability.
    Falls back to Opus 4.5 if needed for complex arbitration.
    
    Returns:
        ChatBedrock: Powerful model instance for arbitration
    """
    logger.info(f"Loading arbitrator model (Claude Sonnet 4.5 Global CRIS) in {BEDROCK_REGION}...")
    
    return ChatBedrock(
        model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region_name=BEDROCK_REGION,
        model_kwargs={
            "temperature": 0.2,  # Lower temperature for more consistent arbitration
            "max_tokens": 8192,
        },
        config=BOTO_CONFIG
    )


def load_model_for_agent(agent_type: str = "safety") -> ChatBedrock:
    """
    Load model optimized for specific agent type.
    
    Agent types:
    - "safety": Safety-critical agents (crew_compliance, maintenance, regulatory)
              Uses Sonnet 4.5 for high accuracy
    - "business": Business optimization agents (network, guest_experience, cargo, finance)
                Uses Haiku 4.5 for speed and cost efficiency
    - "arbitrator": Arbitrator agent for conflict resolution
                  Uses Sonnet 4.5 for balanced reasoning
    
    Args:
        agent_type: Type of agent ("safety", "business", or "arbitrator")
        
    Returns:
        ChatBedrock: Model instance configured for agent type
        
    Raises:
        ValueError: If agent_type is not recognized
        
    Example:
        >>> # Load model for safety agent
        >>> llm = load_model_for_agent("safety")
        >>> # Load model for business agent
        >>> llm = load_model_for_agent("business")
    """
    if agent_type not in AGENT_MODEL_CONFIG:
        raise ValueError(
            f"Unknown agent_type: {agent_type}. "
            f"Valid types: {list(AGENT_MODEL_CONFIG.keys())}"
        )
    
    config = AGENT_MODEL_CONFIG[agent_type]
    logger.info(f"Loading {agent_type} agent model in {BEDROCK_REGION}: {config['reason']}")
    logger.debug(f"   Model ID: {config['model_id']}")
    logger.debug(f"   Temperature: {config['temperature']}")
    logger.debug(f"   Max tokens: {config['max_tokens']}")
    
    return ChatBedrock(
        model_id=config["model_id"],
        region_name=BEDROCK_REGION,
        model_kwargs={
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
        },
        config=BOTO_CONFIG  # Use increased timeout configuration
    )
