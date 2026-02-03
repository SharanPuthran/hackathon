"""Configuration management for SkyMarshal"""

import os
from dotenv import load_dotenv

load_dotenv()

# AWS Configuration (Only provider needed)
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'etihad_aviation')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# Application Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
ENABLE_COST_TRACKING = os.getenv('ENABLE_COST_TRACKING', 'true').lower() == 'true'
MAX_DEBATE_ROUNDS = int(os.getenv('MAX_DEBATE_ROUNDS', 3))
SAFETY_TIMEOUT_SECONDS = int(os.getenv('SAFETY_TIMEOUT_SECONDS', 60))

# Model Configuration - All via AWS Bedrock
# Using GLOBAL cross-region inference profiles (CRIS) for better availability and reduced throttling
# Global endpoints distribute load across multiple regions automatically
AGENT_MODEL_MAP = {
    # Core orchestration - Fast and efficient
    "orchestrator": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Fast workflow coordination with excellent state management"
    },

    # Arbitrator - Strongest available reasoning model
    "arbitrator": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Most powerful reasoning for complex multi-criteria optimization"
    },

    # Safety Agents (critical - using Claude Sonnet 4.5 Global for all reasoning tasks)
    "crew_compliance_agent": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Chain-of-thought reasoning for FTL regulations and safety compliance"
    },
    "maintenance_agent": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Technical reasoning for MEL/AOG analysis with high accuracy"
    },
    "regulatory_agent": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Regulatory compliance analysis with detailed reasoning"
    },

    # Business Agents (using Claude Haiku 4.5 Global for fast impact assessment)
    "network_agent": {
        "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Fast network propagation analysis"
    },
    "guest_experience_agent": {
        "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Excellent customer sentiment and empathy analysis"
    },
    "cargo_agent": {
        "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Fast logistics optimization"
    },
    "finance_agent": {
        "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Cost-effective financial modeling"
    },

    # Execution Agents - Fast and reliable
    "execution_agent": {
        "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "provider": "bedrock",
        "reason": "Global CRIS - Reliable execution coordination with fast response times"
    }
}
