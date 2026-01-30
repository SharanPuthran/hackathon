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
# Using Amazon Nova Premier (currently accessible)
# NOTE: Claude models require use case form submission at: https://pages.awscloud.com/GLOBAL-ln-GC-Bedrock-3pmodel-interest-form-2024.html
AGENT_MODEL_MAP = {
    # Core orchestration - Fast and efficient
    "orchestrator": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Fast workflow coordination with excellent state management"
    },

    # Arbitrator - Strongest available reasoning model
    "arbitrator": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Most powerful reasoning for complex multi-criteria optimization and scenario ranking"
    },

    # Safety Agents (critical - using Nova Premier for all reasoning tasks)
    "crew_compliance_agent": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Chain-of-thought reasoning for FTL regulations and safety compliance"
    },
    "maintenance_agent": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Technical reasoning for MEL/AOG analysis with high accuracy"
    },
    "regulatory_agent": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Regulatory compliance analysis with detailed reasoning"
    },

    # Business Agents (fast models for quick impact assessment and proposals)
    "network_agent": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Fast network propagation analysis with excellent reasoning"
    },
    "guest_experience_agent": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Excellent customer sentiment and empathy analysis"
    },
    "cargo_agent": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Fast logistics optimization with strong reasoning"
    },
    "finance_agent": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Cost-effective financial modeling with strong numerical reasoning"
    },

    # Execution Agents - Fast and reliable
    "execution_agent": {
        "model_id": "us.amazon.nova-premier-v1:0",
        "provider": "bedrock",
        "reason": "Reliable execution coordination with fast response times"
    }
}
