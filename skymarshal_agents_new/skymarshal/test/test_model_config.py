"""
Test model configuration for agent-specific models.

Tests that safety agents use Sonnet 4.5, business agents use Haiku 4.5,
and arbitrator uses Sonnet 4.5 as per requirements 4.1, 4.2, 4.3.
"""

import pytest
from model.load import (
    AGENT_MODEL_CONFIG,
    load_model_for_agent,
)


class TestAgentModelConfig:
    """Test agent-specific model configuration."""

    def test_agent_model_config_exists(self):
        """Test that AGENT_MODEL_CONFIG is defined with all required agent types."""
        assert "safety" in AGENT_MODEL_CONFIG
        assert "business" in AGENT_MODEL_CONFIG
        assert "arbitrator" in AGENT_MODEL_CONFIG

    def test_safety_agent_config(self):
        """Test safety agent configuration uses Sonnet 4.5."""
        config = AGENT_MODEL_CONFIG["safety"]
        
        # Verify model ID is Sonnet 4.5
        assert config["model_id"] == "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        
        # Verify configuration parameters
        assert config["temperature"] == 0.3
        assert config["max_tokens"] == 8192
        assert "reason" in config
        assert "accuracy" in config["reason"].lower()

    def test_business_agent_config(self):
        """Test business agent configuration uses Haiku 4.5."""
        config = AGENT_MODEL_CONFIG["business"]
        
        # Verify model ID is Haiku 4.5
        assert config["model_id"] == "global.anthropic.claude-haiku-4-5-20251001-v1:0"
        
        # Verify configuration parameters
        assert config["temperature"] == 0.3
        assert config["max_tokens"] == 4096  # Reduced for faster responses
        assert "reason" in config
        assert "speed" in config["reason"].lower()

    def test_arbitrator_config(self):
        """Test arbitrator configuration uses Sonnet 4.5."""
        config = AGENT_MODEL_CONFIG["arbitrator"]
        
        # Verify model ID is Sonnet 4.5
        assert config["model_id"] == "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        
        # Verify configuration parameters
        assert config["temperature"] == 0.2  # Lower for consistent arbitration
        assert config["max_tokens"] == 8192
        assert "reason" in config
        assert "reasoning" in config["reason"].lower()

    def test_load_model_for_agent_safety(self):
        """Test loading model for safety agent type."""
        llm = load_model_for_agent("safety")
        
        # Verify model instance is created
        assert llm is not None
        assert hasattr(llm, "model_id")
        assert llm.model_id == "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

    def test_load_model_for_agent_business(self):
        """Test loading model for business agent type."""
        llm = load_model_for_agent("business")
        
        # Verify model instance is created
        assert llm is not None
        assert hasattr(llm, "model_id")
        assert llm.model_id == "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    def test_load_model_for_agent_arbitrator(self):
        """Test loading model for arbitrator agent type."""
        llm = load_model_for_agent("arbitrator")
        
        # Verify model instance is created
        assert llm is not None
        assert hasattr(llm, "model_id")
        assert llm.model_id == "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

    def test_load_model_for_agent_invalid_type(self):
        """Test that invalid agent type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            load_model_for_agent("invalid_type")
        
        assert "Unknown agent_type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)

    def test_model_ids_are_global_cris(self):
        """Test that all model IDs use Global CRIS endpoints."""
        for agent_type, config in AGENT_MODEL_CONFIG.items():
            model_id = config["model_id"]
            assert model_id.startswith("global."), (
                f"{agent_type} agent should use Global CRIS model, "
                f"but uses: {model_id}"
            )

    def test_safety_and_arbitrator_use_same_model(self):
        """Test that safety agents and arbitrator both use Sonnet 4.5."""
        safety_model = AGENT_MODEL_CONFIG["safety"]["model_id"]
        arbitrator_model = AGENT_MODEL_CONFIG["arbitrator"]["model_id"]
        
        assert safety_model == arbitrator_model, (
            "Safety agents and arbitrator should use the same model (Sonnet 4.5)"
        )

    def test_business_uses_different_model(self):
        """Test that business agents use a different model than safety agents."""
        safety_model = AGENT_MODEL_CONFIG["safety"]["model_id"]
        business_model = AGENT_MODEL_CONFIG["business"]["model_id"]
        
        assert safety_model != business_model, (
            "Business agents should use a different model (Haiku 4.5) "
            "than safety agents (Sonnet 4.5)"
        )

    def test_business_has_lower_max_tokens(self):
        """Test that business agents have lower max_tokens for faster responses."""
        safety_tokens = AGENT_MODEL_CONFIG["safety"]["max_tokens"]
        business_tokens = AGENT_MODEL_CONFIG["business"]["max_tokens"]
        
        assert business_tokens < safety_tokens, (
            "Business agents should have lower max_tokens for faster responses"
        )

    def test_arbitrator_has_lowest_temperature(self):
        """Test that arbitrator has lowest temperature for consistent decisions."""
        safety_temp = AGENT_MODEL_CONFIG["safety"]["temperature"]
        business_temp = AGENT_MODEL_CONFIG["business"]["temperature"]
        arbitrator_temp = AGENT_MODEL_CONFIG["arbitrator"]["temperature"]
        
        assert arbitrator_temp <= safety_temp, (
            "Arbitrator should have lowest temperature for consistent decisions"
        )
        assert arbitrator_temp <= business_temp, (
            "Arbitrator should have lowest temperature for consistent decisions"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
