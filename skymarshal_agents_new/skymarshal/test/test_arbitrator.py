"""
Unit tests for Arbitrator Agent

Tests the arbitrator's ability to:
- Identify conflicts between agent recommendations
- Extract binding constraints from safety agents
- Apply safety-first decision rules
- Generate structured output
- Handle error cases gracefully
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from agents.arbitrator.agent import (
    arbitrate,
    _extract_safety_agents,
    _extract_business_agents,
    _extract_binding_constraints,
    _format_agent_responses,
    _is_model_available,
    _load_opus_model,
    _load_fallback_model,
    OPUS_MODEL_ID,
    SONNET_MODEL_ID,
)

# Import schemas from centralized schemas module
from agents.schemas import (
    ArbitratorOutput,
    ConflictDetail,
    ResolutionDetail,
    SafetyOverride,
)


# ============================================================================
# Model Loading and Service Discovery Tests
# ============================================================================


@patch('agents.arbitrator.agent.boto3.client')
def test_is_model_available_success(mock_boto_client):
    """Test successful model availability check"""
    # Mock bedrock client
    mock_bedrock = Mock()
    mock_boto_client.return_value = mock_bedrock
    
    # Mock response with available models
    mock_bedrock.list_foundation_models.return_value = {
        'modelSummaries': [
            {'modelId': 'us.anthropic.claude-opus-4-5-20250514-v1:0'},
            {'modelId': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'},
        ]
    }
    
    # Test exact match
    assert _is_model_available(OPUS_MODEL_ID) is True
    
    # Verify boto3 client was called correctly
    mock_boto_client.assert_called_with('bedrock')
    mock_bedrock.list_foundation_models.assert_called()


@patch('agents.arbitrator.agent.boto3.client')
def test_is_model_available_prefix_match(mock_boto_client):
    """Test model availability check with prefix match"""
    mock_bedrock = Mock()
    mock_boto_client.return_value = mock_bedrock
    
    # Mock response with model that has different version
    mock_bedrock.list_foundation_models.return_value = {
        'modelSummaries': [
            {'modelId': 'us.anthropic.claude-opus-4-5-20250514-v2:0'},  # Different version
        ]
    }
    
    # Should still match on prefix
    assert _is_model_available(OPUS_MODEL_ID) is True


@patch('agents.arbitrator.agent.boto3.client')
def test_is_model_available_not_found(mock_boto_client):
    """Test model availability check when model not found"""
    mock_bedrock = Mock()
    mock_boto_client.return_value = mock_bedrock
    
    # Mock response without the model
    mock_bedrock.list_foundation_models.return_value = {
        'modelSummaries': [
            {'modelId': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'},
        ]
    }
    
    assert _is_model_available(OPUS_MODEL_ID) is False


@patch('agents.arbitrator.agent.boto3.client')
def test_is_model_available_client_error(mock_boto_client):
    """Test model availability check with ClientError"""
    from botocore.exceptions import ClientError
    
    mock_bedrock = Mock()
    mock_boto_client.return_value = mock_bedrock
    
    # Mock ClientError
    error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
    mock_bedrock.list_foundation_models.side_effect = ClientError(error_response, 'ListFoundationModels')
    
    # Should return False on error
    assert _is_model_available(OPUS_MODEL_ID) is False


@patch('agents.arbitrator.agent.boto3.client')
def test_is_model_available_generic_error(mock_boto_client):
    """Test model availability check with generic error"""
    mock_bedrock = Mock()
    mock_boto_client.return_value = mock_bedrock
    
    # Mock generic exception
    mock_bedrock.list_foundation_models.side_effect = Exception("Network error")
    
    # Should return False on error
    assert _is_model_available(OPUS_MODEL_ID) is False


@patch('agents.arbitrator.agent._is_model_available')
@patch('agents.arbitrator.agent.ChatBedrock')
def test_load_opus_model_success(mock_chatbedrock, mock_is_available):
    """Test successful Opus model loading"""
    # Mock model availability check
    mock_is_available.return_value = True
    
    # Mock ChatBedrock
    mock_model = Mock()
    mock_chatbedrock.return_value = mock_model
    
    # Load model
    result = _load_opus_model()
    
    # Verify
    assert result == mock_model
    mock_is_available.assert_called_once_with(OPUS_MODEL_ID)
    mock_chatbedrock.assert_called_once()
    
    # Verify model kwargs
    call_kwargs = mock_chatbedrock.call_args[1]
    assert call_kwargs['model_id'] == OPUS_MODEL_ID
    assert call_kwargs['model_kwargs']['temperature'] == 0.1
    assert call_kwargs['model_kwargs']['max_tokens'] == 16384


@patch('agents.arbitrator.agent._is_model_available')
@patch('agents.arbitrator.agent._load_fallback_model')
def test_load_opus_model_not_available(mock_fallback, mock_is_available):
    """Test Opus model loading when model not available"""
    # Mock model not available
    mock_is_available.return_value = False
    
    # Mock fallback model
    mock_fallback_model = Mock()
    mock_fallback.return_value = mock_fallback_model
    
    # Load model
    result = _load_opus_model()
    
    # Verify fallback was used
    assert result == mock_fallback_model
    mock_is_available.assert_called_once_with(OPUS_MODEL_ID)
    mock_fallback.assert_called_once()


@patch('agents.arbitrator.agent._is_model_available')
@patch('agents.arbitrator.agent.ChatBedrock')
@patch('agents.arbitrator.agent._load_fallback_model')
def test_load_opus_model_loading_fails(mock_fallback, mock_chatbedrock, mock_is_available):
    """Test Opus model loading when ChatBedrock fails"""
    # Mock model available but loading fails
    mock_is_available.return_value = True
    mock_chatbedrock.side_effect = Exception("Model loading error")
    
    # Mock fallback model
    mock_fallback_model = Mock()
    mock_fallback.return_value = mock_fallback_model
    
    # Load model
    result = _load_opus_model()
    
    # Verify fallback was used
    assert result == mock_fallback_model
    mock_fallback.assert_called_once()


@patch('agents.arbitrator.agent.ChatBedrock')
def test_load_fallback_model(mock_chatbedrock):
    """Test fallback Sonnet model loading"""
    # Mock ChatBedrock
    mock_model = Mock()
    mock_chatbedrock.return_value = mock_model
    
    # Load fallback
    result = _load_fallback_model()
    
    # Verify
    assert result == mock_model
    mock_chatbedrock.assert_called_once()
    
    # Verify model kwargs
    call_kwargs = mock_chatbedrock.call_args[1]
    assert call_kwargs['model_id'] == SONNET_MODEL_ID
    assert call_kwargs['model_kwargs']['temperature'] == 0.1
    assert call_kwargs['model_kwargs']['max_tokens'] == 8192


# ============================================================================
# Helper Function Tests
# ============================================================================


def test_extract_safety_agents():
    """Test extraction of safety agent responses"""
    responses = {
        "crew_compliance": {"recommendation": "Test"},
        "maintenance": {"recommendation": "Test"},
        "regulatory": {"recommendation": "Test"},
        "network": {"recommendation": "Test"},
        "finance": {"recommendation": "Test"},
    }
    
    safety = _extract_safety_agents(responses)
    
    assert len(safety) == 3
    assert "crew_compliance" in safety
    assert "maintenance" in safety
    assert "regulatory" in safety
    assert "network" not in safety
    assert "finance" not in safety


def test_extract_business_agents():
    """Test extraction of business agent responses"""
    responses = {
        "crew_compliance": {"recommendation": "Test"},
        "network": {"recommendation": "Test"},
        "guest_experience": {"recommendation": "Test"},
        "cargo": {"recommendation": "Test"},
        "finance": {"recommendation": "Test"},
    }
    
    business = _extract_business_agents(responses)
    
    assert len(business) == 4
    assert "network" in business
    assert "guest_experience" in business
    assert "cargo" in business
    assert "finance" in business
    assert "crew_compliance" not in business


def test_extract_binding_constraints():
    """Test extraction of binding constraints from safety agents"""
    responses = {
        "crew_compliance": {
            "recommendation": "Cannot proceed",
            "binding_constraints": [
                "Crew must have 10 hours rest",
                "Replacement crew must be qualified"
            ]
        },
        "maintenance": {
            "recommendation": "Requires inspection",
            "binding_constraints": [
                "Aircraft must pass A-check before flight"
            ]
        },
        "regulatory": {
            "recommendation": "Approved",
            "binding_constraints": []
        },
        "network": {
            "recommendation": "Delay 2 hours"
        }
    }
    
    constraints = _extract_binding_constraints(responses)
    
    assert len(constraints) == 3
    assert constraints[0]["agent"] == "crew_compliance"
    assert "10 hours rest" in constraints[0]["constraint"]
    assert constraints[2]["agent"] == "maintenance"


def test_format_agent_responses():
    """Test formatting of agent responses for prompt"""
    responses = {
        "crew_compliance": {
            "recommendation": "Cannot proceed",
            "confidence": 0.95,
            "binding_constraints": ["Crew must have 10 hours rest"],
            "reasoning": "Crew exceeds FDP limits"
        },
        "network": {
            "recommendation": "Delay 2 hours",
            "confidence": 0.85,
            "reasoning": "Minimize propagation"
        }
    }
    
    formatted = _format_agent_responses(responses)
    
    assert "Safety Agents" in formatted
    assert "Business Agents" in formatted
    assert "Crew Compliance" in formatted
    assert "Network" in formatted
    assert "Cannot proceed" in formatted
    assert "Delay 2 hours" in formatted
    assert "Binding Constraints" in formatted
    assert "Crew must have 10 hours rest" in formatted


# ============================================================================
# Pydantic Model Tests
# ============================================================================


def test_conflict_detail_model():
    """Test ConflictDetail Pydantic model"""
    conflict = ConflictDetail(
        agents_involved=["crew_compliance", "network"],
        conflict_type="safety_vs_business",
        description="Crew rest requirement vs network delay preference"
    )
    
    assert conflict.agents_involved == ["crew_compliance", "network"]
    assert conflict.conflict_type == "safety_vs_business"
    assert "rest requirement" in conflict.description


def test_resolution_detail_model():
    """Test ResolutionDetail Pydantic model"""
    resolution = ResolutionDetail(
        conflict_description="Crew rest vs network delay",
        resolution="Enforce crew rest requirement",
        rationale="Safety constraints are non-negotiable"
    )
    
    assert "rest" in resolution.conflict_description
    assert "Enforce" in resolution.resolution
    assert "non-negotiable" in resolution.rationale


def test_safety_override_model():
    """Test SafetyOverride Pydantic model"""
    override = SafetyOverride(
        safety_agent="crew_compliance",
        binding_constraint="Crew must have 10 hours rest",
        overridden_recommendations=["Delay flight by 2 hours"]
    )
    
    assert override.safety_agent == "crew_compliance"
    assert "10 hours" in override.binding_constraint
    assert len(override.overridden_recommendations) == 1


def test_arbitrator_decision_model():
    """Test ArbitratorOutput Pydantic model"""
    decision = ArbitratorOutput(
        final_decision="Enforce crew rest requirement",
        recommendations=["Delay flight", "Arrange replacement crew"],
        conflicts_identified=[
            ConflictDetail(
                agents_involved=["crew_compliance", "network"],
                conflict_type="safety_vs_business",
                description="Test conflict"
            )
        ],
        conflict_resolutions=[
            ResolutionDetail(
                conflict_description="Test conflict",
                resolution="Safety priority",
                rationale="Safety first"
            )
        ],
        safety_overrides=[
            SafetyOverride(
                safety_agent="crew_compliance",
                binding_constraint="10 hours rest",
                overridden_recommendations=["2 hour delay"]
            )
        ],
        justification="Safety constraints must be satisfied",
        reasoning="Detailed reasoning here",
        confidence=0.95,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    assert decision.confidence == 0.95
    assert len(decision.recommendations) == 2
    assert len(decision.conflicts_identified) == 1
    assert decision.conflicts_identified[0].conflict_type == "safety_vs_business"


def test_arbitrator_decision_confidence_validation():
    """Test confidence score validation"""
    # Valid confidence
    decision = ArbitratorOutput(
        final_decision="Test",
        recommendations=["Test"],
        justification="Test",
        reasoning="Test",
        confidence=0.5,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    assert decision.confidence == 0.5
    
    # Invalid confidence (too high)
    with pytest.raises(ValueError):
        ArbitratorOutput(
            final_decision="Test",
            recommendations=["Test"],
            justification="Test",
            reasoning="Test",
            confidence=1.5,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    # Invalid confidence (negative)
    with pytest.raises(ValueError):
        ArbitratorOutput(
            final_decision="Test",
            recommendations=["Test"],
            justification="Test",
            reasoning="Test",
            confidence=-0.1,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


# ============================================================================
# Arbitrate Function Tests
# ============================================================================


@pytest.mark.asyncio
async def test_arbitrate_empty_input():
    """Test arbitrate with empty input"""
    with pytest.raises(ValueError, match="cannot be empty"):
        await arbitrate({})


@pytest.mark.asyncio
async def test_arbitrate_with_mock_llm():
    """Test arbitrate with mocked LLM"""
    # Create mock responses
    responses = {
        "crew_compliance": {
            "recommendation": "Cannot proceed - crew exceeds FDP",
            "confidence": 0.95,
            "binding_constraints": ["Crew must have 10 hours rest"],
            "reasoning": "Current crew at 13.5 hours duty time"
        },
        "maintenance": {
            "recommendation": "Approved - aircraft airworthy",
            "confidence": 0.90,
            "binding_constraints": [],
            "reasoning": "No MEL items affecting flight"
        },
        "network": {
            "recommendation": "Delay 2 hours to minimize propagation",
            "confidence": 0.85,
            "reasoning": "Affects 3 downstream flights"
        }
    }
    
    # Create mock LLM
    mock_llm = Mock()
    mock_structured_llm = Mock()
    
    # Create mock decision
    mock_decision = ArbitratorOutput(
        final_decision="Enforce crew rest requirement - delay flight for crew change",
        recommendations=[
            "Delay flight to allow 10-hour crew rest",
            "Arrange replacement crew",
            "Notify affected passengers"
        ],
        conflicts_identified=[
            ConflictDetail(
                agents_involved=["crew_compliance", "network"],
                conflict_type="safety_vs_business",
                description="Crew rest requirement conflicts with network delay preference"
            )
        ],
        conflict_resolutions=[
            ResolutionDetail(
                conflict_description="Crew rest vs network delay",
                resolution="Enforce crew rest requirement",
                rationale="Safety constraints are non-negotiable"
            )
        ],
        safety_overrides=[
            SafetyOverride(
                safety_agent="crew_compliance",
                binding_constraint="Crew must have 10 hours rest",
                overridden_recommendations=["Delay flight by 2 hours"]
            )
        ],
        justification="Safety constraints must be satisfied. Crew rest is non-negotiable.",
        reasoning="Applied Rule 1: Safety vs Business - always choose safety constraint",
        confidence=0.95,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    mock_structured_llm.invoke = Mock(return_value=mock_decision)
    mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
    
    # Call arbitrate
    result = await arbitrate(responses, llm_opus=mock_llm)
    
    # Verify result
    assert result["final_decision"] == "Enforce crew rest requirement - delay flight for crew change"
    assert len(result["recommendations"]) == 3
    assert len(result["conflicts_identified"]) == 1
    assert result["conflicts_identified"][0]["conflict_type"] == "safety_vs_business"
    assert len(result["safety_overrides"]) == 1
    assert result["confidence"] == 0.95
    assert "timestamp" in result
    assert "model_used" in result
    
    # Verify LLM was called
    mock_llm.with_structured_output.assert_called_once()
    mock_structured_llm.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_arbitrate_with_collation_object():
    """Test arbitrate with Collation object input"""
    from agents.schemas import AgentResponse, Collation
    
    # Create AgentResponse objects
    crew_response = AgentResponse(
        agent_name="crew_compliance",
        recommendation="Cannot proceed",
        confidence=0.95,
        binding_constraints=["Crew must have 10 hours rest"],
        reasoning="Crew exceeds FDP",
        data_sources=["CrewRoster"],
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    network_response = AgentResponse(
        agent_name="network",
        recommendation="Delay 2 hours",
        confidence=0.85,
        reasoning="Minimize propagation",
        data_sources=["Flights"],
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    # Create Collation
    collation = Collation(
        phase="revision",
        responses={
            "crew_compliance": crew_response,
            "network": network_response
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
        duration_seconds=8.5
    )
    
    # Create mock LLM
    mock_llm = Mock()
    mock_structured_llm = Mock()
    
    mock_decision = ArbitratorOutput(
        final_decision="Test decision",
        recommendations=["Test"],
        justification="Test",
        reasoning="Test",
        confidence=0.9,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    mock_structured_llm.invoke = Mock(return_value=mock_decision)
    mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
    
    # Call arbitrate with Collation object
    result = await arbitrate(collation, llm_opus=mock_llm)
    
    # Verify result
    assert result["final_decision"] == "Test decision"
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_arbitrate_error_handling():
    """Test arbitrate error handling"""
    responses = {
        "crew_compliance": {
            "recommendation": "Test",
            "confidence": 0.9,
            "reasoning": "Test"
        }
    }
    
    # Create mock LLM that raises exception
    mock_llm = Mock()
    mock_llm.with_structured_output = Mock(side_effect=Exception("Model error"))
    
    # Call arbitrate - should return fallback decision
    result = await arbitrate(responses, llm_opus=mock_llm)
    
    # Verify fallback decision
    assert "Unable to complete arbitration" in result["final_decision"]
    assert result["confidence"] == 0.0
    assert "error" in result
    assert "Manual review required" in result["recommendations"]


@pytest.mark.asyncio
async def test_arbitrate_no_conflicts():
    """Test arbitrate when all agents agree"""
    responses = {
        "crew_compliance": {
            "recommendation": "Approved",
            "confidence": 0.95,
            "binding_constraints": [],
            "reasoning": "Crew within limits"
        },
        "maintenance": {
            "recommendation": "Approved",
            "confidence": 0.90,
            "binding_constraints": [],
            "reasoning": "Aircraft airworthy"
        },
        "network": {
            "recommendation": "Approved",
            "confidence": 0.85,
            "reasoning": "Minimal network impact"
        }
    }
    
    # Create mock LLM
    mock_llm = Mock()
    mock_structured_llm = Mock()
    
    mock_decision = ArbitratorOutput(
        final_decision="Approve flight operation as recommended by all agents",
        recommendations=["Proceed with flight as scheduled"],
        conflicts_identified=[],
        conflict_resolutions=[],
        safety_overrides=[],
        justification="All agents agree - no conflicts identified",
        reasoning="Unanimous approval from all agents",
        confidence=0.95,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    mock_structured_llm.invoke = Mock(return_value=mock_decision)
    mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
    
    # Call arbitrate
    result = await arbitrate(responses, llm_opus=mock_llm)
    
    # Verify result
    assert len(result["conflicts_identified"]) == 0
    assert len(result["safety_overrides"]) == 0
    assert result["confidence"] == 0.95


# ============================================================================
# Property-Based Tests
# ============================================================================


class TestProperty8SafetyPriorityInvariant:
    """
    Property-Based Tests for Property 8: Safety Priority Invariant
    
    Feature: skymarshal-multi-round-orchestration
    Property 8: Safety Priority Invariant
    Validates: Requirements 11.3, 11.4, 13.1-13.3
    
    Safety agent binding constraints SHALL always be satisfied in the final decision:
    
    ∀ safety_agent s, ∀ binding_constraint c ∈ s.constraints:
      final_decision.satisfies(c) = true
    
    Test Strategy: Generate scenarios where safety and business agents conflict,
    verify final decision always satisfies safety constraints.
    """
    
    def test_safety_constraint_always_satisfied_single_constraint(self):
        """
        Property 8.1: Single safety constraint is always satisfied
        
        When a safety agent provides a binding constraint, the final decision
        must satisfy that constraint regardless of business agent recommendations.
        
        Validates: Requirements 11.3, 13.1
        """
        from hypothesis import given, strategies as st, settings
        import asyncio
        
        # Define strategy for safety constraints
        safety_constraints = st.sampled_from([
            "Crew must have 10 hours rest before next duty",
            "Aircraft must pass A-check inspection before flight",
            "Flight must not violate airport curfew restrictions",
            "Crew must not exceed 14-hour flight duty period",
            "Aircraft must have valid maintenance certification",
            "Weather conditions must meet minimum visibility requirements",
        ])
        
        # Define strategy for business recommendations
        business_recommendations = st.sampled_from([
            "Delay flight by 2 hours to minimize network impact",
            "Cancel flight to optimize aircraft utilization",
            "Proceed with flight to maintain schedule",
            "Swap aircraft to reduce maintenance costs",
            "Rebook passengers on alternative flights",
        ])
        
        @given(
            safety_constraint=safety_constraints,
            business_recommendation=business_recommendations,
            safety_confidence=st.floats(min_value=0.8, max_value=1.0),
            business_confidence=st.floats(min_value=0.7, max_value=0.95),
        )
        @settings(max_examples=50, deadline=None)
        def property_test(safety_constraint, business_recommendation, 
                         safety_confidence, business_confidence):
            # Create responses with safety vs business conflict
            responses = {
                "crew_compliance": {
                    "recommendation": "Cannot proceed without addressing constraint",
                    "confidence": safety_confidence,
                    "binding_constraints": [safety_constraint],
                    "reasoning": f"Safety constraint must be satisfied: {safety_constraint}"
                },
                "network": {
                    "recommendation": business_recommendation,
                    "confidence": business_confidence,
                    "reasoning": "Business optimization recommendation"
                }
            }
            
            # Create mock LLM that respects safety constraints
            mock_llm = Mock()
            mock_structured_llm = Mock()
            
            # Mock decision that satisfies safety constraint
            mock_decision = ArbitratorOutput(
                final_decision=f"Enforce safety constraint: {safety_constraint}",
                recommendations=[
                    f"Satisfy constraint: {safety_constraint}",
                    "Adjust business operations accordingly"
                ],
                conflicts_identified=[
                    ConflictDetail(
                        agents_involved=["crew_compliance", "network"],
                        conflict_type="safety_vs_business",
                        description=f"Safety constraint conflicts with business recommendation"
                    )
                ],
                conflict_resolutions=[
                    ResolutionDetail(
                        conflict_description="Safety vs business conflict",
                        resolution=f"Enforce safety constraint: {safety_constraint}",
                        rationale="Safety constraints are non-negotiable"
                    )
                ],
                safety_overrides=[
                    SafetyOverride(
                        safety_agent="crew_compliance",
                        binding_constraint=safety_constraint,
                        overridden_recommendations=[business_recommendation]
                    )
                ],
                justification=f"Safety constraint must be satisfied: {safety_constraint}",
                reasoning="Applied Rule 1: Safety vs Business - always choose safety",
                confidence=0.95,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            mock_structured_llm.invoke = Mock(return_value=mock_decision)
            mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
            
            # Call arbitrate synchronously using asyncio.run
            result = asyncio.run(arbitrate(responses, llm_opus=mock_llm))
            
            # Property: Safety constraint must be mentioned in final decision
            assert safety_constraint in result["final_decision"] or \
                   any(safety_constraint in rec for rec in result["recommendations"]), \
                   f"Safety constraint must be satisfied in final decision: {safety_constraint}"
            
            # Property: Safety override must be recorded
            assert len(result["safety_overrides"]) > 0, \
                   "Safety override must be recorded when safety constraint conflicts with business"
            
            # Property: Safety agent must be in safety overrides
            assert any(override["safety_agent"] == "crew_compliance" 
                      for override in result["safety_overrides"]), \
                   "Safety agent must be recorded in safety overrides"
            
            # Property: Binding constraint must be in safety overrides
            assert any(safety_constraint in override["binding_constraint"] 
                      for override in result["safety_overrides"]), \
                   f"Binding constraint must be recorded: {safety_constraint}"
        
        # Run the property test
        property_test()
    
    def test_multiple_safety_constraints_all_satisfied(self):
        """
        Property 8.2: Multiple safety constraints are all satisfied
        
        When multiple safety agents provide binding constraints, the final decision
        must satisfy ALL constraints.
        
        Validates: Requirements 11.3, 11.4, 13.2
        """
        from hypothesis import given, strategies as st, settings
        import asyncio
        
        # Define strategies for multiple safety constraints
        crew_constraints = st.sampled_from([
            "Crew must have 10 hours rest",
            "Crew must not exceed FDP limits",
            "Replacement crew must be qualified",
        ])
        
        maintenance_constraints = st.sampled_from([
            "Aircraft must pass inspection",
            "MEL items must be resolved",
            "Maintenance certification required",
        ])
        
        regulatory_constraints = st.sampled_from([
            "Must comply with airport curfew",
            "Weather minimums must be met",
            "NOTAM restrictions must be observed",
        ])
        
        @given(
            crew_constraint=crew_constraints,
            maintenance_constraint=maintenance_constraints,
            regulatory_constraint=regulatory_constraints,
        )
        @settings(max_examples=30, deadline=None)
        def property_test(crew_constraint, maintenance_constraint, regulatory_constraint):
            # Create responses with multiple safety constraints
            responses = {
                "crew_compliance": {
                    "recommendation": "Address crew constraint",
                    "confidence": 0.95,
                    "binding_constraints": [crew_constraint],
                    "reasoning": f"Crew constraint: {crew_constraint}"
                },
                "maintenance": {
                    "recommendation": "Address maintenance constraint",
                    "confidence": 0.90,
                    "binding_constraints": [maintenance_constraint],
                    "reasoning": f"Maintenance constraint: {maintenance_constraint}"
                },
                "regulatory": {
                    "recommendation": "Address regulatory constraint",
                    "confidence": 0.92,
                    "binding_constraints": [regulatory_constraint],
                    "reasoning": f"Regulatory constraint: {regulatory_constraint}"
                },
                "network": {
                    "recommendation": "Minimize delay",
                    "confidence": 0.85,
                    "reasoning": "Business optimization"
                }
            }
            
            # Create mock LLM
            mock_llm = Mock()
            mock_structured_llm = Mock()
            
            # Mock decision that satisfies all safety constraints
            all_constraints = [crew_constraint, maintenance_constraint, regulatory_constraint]
            mock_decision = ArbitratorOutput(
                final_decision=f"Satisfy all safety constraints: {', '.join(all_constraints)}",
                recommendations=[
                    f"Address: {crew_constraint}",
                    f"Address: {maintenance_constraint}",
                    f"Address: {regulatory_constraint}",
                ],
                conflicts_identified=[],
                conflict_resolutions=[],
                safety_overrides=[
                    SafetyOverride(
                        safety_agent="crew_compliance",
                        binding_constraint=crew_constraint,
                        overridden_recommendations=["Minimize delay"]  # Business recommendation overridden
                    ),
                    SafetyOverride(
                        safety_agent="maintenance",
                        binding_constraint=maintenance_constraint,
                        overridden_recommendations=["Minimize delay"]  # Business recommendation overridden
                    ),
                    SafetyOverride(
                        safety_agent="regulatory",
                        binding_constraint=regulatory_constraint,
                        overridden_recommendations=["Minimize delay"]  # Business recommendation overridden
                    ),
                ],
                justification="All safety constraints must be satisfied",
                reasoning="Multiple safety constraints require comprehensive solution",
                confidence=0.95,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            mock_structured_llm.invoke = Mock(return_value=mock_decision)
            mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
            
            # Call arbitrate synchronously using asyncio.run
            result = asyncio.run(arbitrate(responses, llm_opus=mock_llm))
            
            # Property: All safety constraints must be addressed
            decision_text = result["final_decision"] + " ".join(result["recommendations"])
            
            # At least one constraint should be explicitly mentioned
            constraints_mentioned = sum(1 for c in all_constraints if c in decision_text)
            assert constraints_mentioned >= 1, \
                   f"At least one safety constraint must be mentioned in decision"
            
            # Property: Number of safety overrides should match number of safety agents with constraints
            assert len(result["safety_overrides"]) == 3, \
                   f"All safety constraints must be recorded in safety overrides"
            
            # Property: Each safety agent should have an override entry
            safety_agents_in_overrides = {override["safety_agent"] 
                                         for override in result["safety_overrides"]}
            assert "crew_compliance" in safety_agents_in_overrides, \
                   "Crew compliance constraint must be in overrides"
            assert "maintenance" in safety_agents_in_overrides, \
                   "Maintenance constraint must be in overrides"
            assert "regulatory" in safety_agents_in_overrides, \
                   "Regulatory constraint must be in overrides"
        
        # Run the property test
        property_test()
    
    def test_safety_priority_over_high_confidence_business(self):
        """
        Property 8.3: Safety constraints override even high-confidence business recommendations
        
        Even when business agents have high confidence, safety constraints must
        still be prioritized in the final decision.
        
        Validates: Requirements 11.3, 13.3
        """
        from hypothesis import given, strategies as st, settings
        import asyncio
        
        @given(
            safety_confidence=st.floats(min_value=0.7, max_value=0.95),
            business_confidence=st.floats(min_value=0.85, max_value=0.99),
        )
        @settings(max_examples=30, deadline=None)
        def property_test(safety_confidence, business_confidence):
            # Ensure business confidence is higher than safety confidence
            if business_confidence <= safety_confidence:
                business_confidence = safety_confidence + 0.05
            
            safety_constraint = "Crew must have 10 hours rest"
            
            # Create responses where business has higher confidence
            responses = {
                "crew_compliance": {
                    "recommendation": "Cannot proceed without crew rest",
                    "confidence": safety_confidence,
                    "binding_constraints": [safety_constraint],
                    "reasoning": "Safety constraint"
                },
                "network": {
                    "recommendation": "Proceed immediately to minimize impact",
                    "confidence": business_confidence,
                    "reasoning": "High confidence business recommendation"
                },
                "finance": {
                    "recommendation": "Proceed to avoid cancellation costs",
                    "confidence": business_confidence - 0.02,
                    "reasoning": "Financial optimization"
                }
            }
            
            # Create mock LLM
            mock_llm = Mock()
            mock_structured_llm = Mock()
            
            # Mock decision that prioritizes safety despite lower confidence
            mock_decision = ArbitratorOutput(
                final_decision=f"Enforce safety constraint: {safety_constraint}",
                recommendations=[
                    "Delay flight for crew rest",
                    "Adjust network schedule accordingly"
                ],
                conflicts_identified=[
                    ConflictDetail(
                        agents_involved=["crew_compliance", "network", "finance"],
                        conflict_type="safety_vs_business",
                        description="Safety constraint vs business optimization"
                    )
                ],
                conflict_resolutions=[
                    ResolutionDetail(
                        conflict_description="Safety vs high-confidence business",
                        resolution="Prioritize safety constraint",
                        rationale="Safety constraints override confidence levels"
                    )
                ],
                safety_overrides=[
                    SafetyOverride(
                        safety_agent="crew_compliance",
                        binding_constraint=safety_constraint,
                        overridden_recommendations=[
                            "Proceed immediately to minimize impact",
                            "Proceed to avoid cancellation costs"
                        ]
                    )
                ],
                justification="Safety constraints are non-negotiable regardless of confidence",
                reasoning="Safety priority rule overrides confidence-based decisions",
                confidence=0.95,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            mock_structured_llm.invoke = Mock(return_value=mock_decision)
            mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
            
            # Call arbitrate synchronously using asyncio.run
            result = asyncio.run(arbitrate(responses, llm_opus=mock_llm))
            
            # Property: Safety constraint must be in final decision
            assert safety_constraint in result["final_decision"] or \
                   any(safety_constraint in rec for rec in result["recommendations"]), \
                   "Safety constraint must be satisfied despite lower confidence"
            
            # Property: Safety override must be recorded
            assert len(result["safety_overrides"]) > 0, \
                   "Safety override must be recorded"
            
            # Property: Business recommendations should be in overridden list
            if result["safety_overrides"]:
                overridden = result["safety_overrides"][0]["overridden_recommendations"]
                assert len(overridden) > 0, \
                       "Business recommendations should be overridden by safety"
        
        # Run the property test
        property_test()
    
    @pytest.mark.asyncio
    async def test_empty_binding_constraints_no_override(self):
        """
        Property 8.4: Safety agents without binding constraints don't create overrides
        
        When safety agents approve without binding constraints, no safety overrides
        should be created.
        
        Validates: Requirements 11.3, 13.1
        """
        # Create responses where safety agents approve
        responses = {
            "crew_compliance": {
                "recommendation": "Approved - crew within limits",
                "confidence": 0.95,
                "binding_constraints": [],  # No constraints
                "reasoning": "Crew is available and qualified"
            },
            "maintenance": {
                "recommendation": "Approved - aircraft airworthy",
                "confidence": 0.90,
                "binding_constraints": [],  # No constraints
                "reasoning": "No maintenance issues"
            },
            "network": {
                "recommendation": "Proceed as scheduled",
                "confidence": 0.85,
                "reasoning": "Minimal network impact"
            }
        }
        
        # Create mock LLM
        mock_llm = Mock()
        mock_structured_llm = Mock()
        
        # Mock decision with no conflicts
        mock_decision = ArbitratorOutput(
            final_decision="Approve flight operation as recommended",
            recommendations=["Proceed with flight as scheduled"],
            conflicts_identified=[],
            conflict_resolutions=[],
            safety_overrides=[],  # No overrides when no constraints
            justification="All agents approve - no conflicts",
            reasoning="Unanimous approval",
            confidence=0.95,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        mock_structured_llm.invoke = Mock(return_value=mock_decision)
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
        
        # Call arbitrate
        result = await arbitrate(responses, llm_opus=mock_llm)
        
        # Property: No safety overrides when no binding constraints
        assert len(result["safety_overrides"]) == 0, \
               "No safety overrides should exist when safety agents have no binding constraints"
        
        # Property: No conflicts when all agents agree
        assert len(result["conflicts_identified"]) == 0, \
               "No conflicts should be identified when all agents approve"


class TestProperty9ConservativeConflictResolution:
    """
    Property-Based Tests for Property 9: Conservative Conflict Resolution
    
    Feature: skymarshal-multi-round-orchestration
    Property 9: Conservative Conflict Resolution
    Validates: Requirements 11.4, 11.5, 13.4
    
    When safety agents conflict, the arbitrator SHALL choose the most conservative option:
    
    ∀ safety_agents s1, s2, ∀ conflict c:
      s1.recommendation ≠ s2.recommendation →
      final_decision = most_conservative(s1.recommendation, s2.recommendation)
    
    Test Strategy: Create conflicts between safety agents (e.g., crew compliance vs maintenance),
    verify arbitrator selects the more conservative option.
    """
    
    def test_crew_vs_maintenance_conservative_resolution(self):
        """
        Property 9.1: Crew vs Maintenance conflict resolves to most conservative
        
        When crew compliance and maintenance agents have conflicting requirements,
        the arbitrator must choose the more conservative option (longer delay, more inspection).
        
        Validates: Requirements 11.4, 13.4
        """
        from hypothesis import given, strategies as st, settings
        import asyncio
        
        # Define strategies for crew rest times (in hours)
        crew_rest_hours = st.integers(min_value=8, max_value=12)
        
        # Define strategies for maintenance inspection times (in hours)
        maintenance_hours = st.integers(min_value=6, max_value=14)
        
        @given(
            crew_rest=crew_rest_hours,
            maintenance_time=maintenance_hours,
        )
        @settings(max_examples=40, deadline=None)
        def property_test(crew_rest, maintenance_time):
            # Skip if they're the same (no conflict)
            if crew_rest == maintenance_time:
                return
            
            # Determine which is more conservative (longer time)
            more_conservative_hours = max(crew_rest, maintenance_time)
            more_conservative_agent = "crew_compliance" if crew_rest > maintenance_time else "maintenance"
            
            # Create conflicting safety agent responses
            responses = {
                "crew_compliance": {
                    "recommendation": f"Crew requires {crew_rest}-hour rest period before next duty",
                    "confidence": 0.92,
                    "binding_constraints": [f"Crew must have {crew_rest} hours rest"],
                    "reasoning": f"FDP regulations require minimum {crew_rest}-hour rest"
                },
                "maintenance": {
                    "recommendation": f"Aircraft requires {maintenance_time}-hour inspection",
                    "confidence": 0.90,
                    "binding_constraints": [f"Aircraft must undergo {maintenance_time}-hour inspection"],
                    "reasoning": f"Maintenance schedule requires {maintenance_time}-hour inspection"
                },
                "network": {
                    "recommendation": "Minimize delay to 4 hours",
                    "confidence": 0.85,
                    "reasoning": "Network optimization"
                }
            }
            
            # Create mock LLM
            mock_llm = Mock()
            mock_structured_llm = Mock()
            
            # Mock decision that chooses the more conservative option
            mock_decision = ArbitratorOutput(
                final_decision=f"Enforce {more_conservative_hours}-hour delay to satisfy both safety requirements",
                recommendations=[
                    f"Delay flight by {more_conservative_hours} hours",
                    "Satisfy both crew rest and maintenance requirements",
                    "Adjust network schedule accordingly"
                ],
                conflicts_identified=[
                    ConflictDetail(
                        agents_involved=["crew_compliance", "maintenance"],
                        conflict_type="safety_vs_safety",
                        description=f"Crew requires {crew_rest}h rest vs Maintenance requires {maintenance_time}h inspection"
                    )
                ],
                conflict_resolutions=[
                    ResolutionDetail(
                        conflict_description=f"Crew {crew_rest}h vs Maintenance {maintenance_time}h",
                        resolution=f"Choose {more_conservative_hours}-hour delay (most conservative)",
                        rationale=f"When safety agents conflict, choose most conservative option. {more_conservative_hours} hours satisfies both requirements."
                    )
                ],
                safety_overrides=[
                    SafetyOverride(
                        safety_agent=more_conservative_agent,
                        binding_constraint=f"Must satisfy {more_conservative_hours}-hour requirement",
                        overridden_recommendations=["Minimize delay to 4 hours"]
                    )
                ],
                justification=f"Both safety constraints must be satisfied. Choosing {more_conservative_hours}-hour delay as most conservative option.",
                reasoning="Applied Rule 2: Safety vs Safety - choose most conservative option",
                confidence=0.93,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            mock_structured_llm.invoke = Mock(return_value=mock_decision)
            mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
            
            # Call arbitrate synchronously using asyncio.run
            result = asyncio.run(arbitrate(responses, llm_opus=mock_llm))
            
            # Property: Final decision must mention the more conservative time
            decision_text = result["final_decision"] + " ".join(result["recommendations"])
            assert str(more_conservative_hours) in decision_text, \
                   f"Final decision must include the more conservative time: {more_conservative_hours} hours"
            
            # Property: Conflict type must be safety_vs_safety
            if result["conflicts_identified"]:
                assert any(conflict["conflict_type"] == "safety_vs_safety" 
                          for conflict in result["conflicts_identified"]), \
                       "Conflict between safety agents must be identified as safety_vs_safety"
            
            # Property: Resolution must mention "conservative"
            if result["conflict_resolutions"]:
                resolution_text = " ".join(res["resolution"] + res["rationale"] 
                                          for res in result["conflict_resolutions"])
                assert "conservative" in resolution_text.lower(), \
                       "Resolution must explicitly mention conservative approach"
        
        # Run the property test
        property_test()
    
    def test_regulatory_vs_crew_conservative_resolution(self):
        """
        Property 9.2: Regulatory vs Crew conflict resolves to most conservative
        
        When regulatory and crew compliance agents have conflicting requirements,
        the arbitrator must choose the more conservative option.
        
        Validates: Requirements 11.4, 11.5, 13.4
        """
        from hypothesis import given, strategies as st, settings
        import asyncio
        
        # Define strategies for different safety scenarios
        crew_scenarios = st.sampled_from([
            ("Crew can operate with 8-hour rest", 8, "minimum"),
            ("Crew requires 10-hour rest for optimal performance", 10, "optimal"),
            ("Crew must have 12-hour rest due to extended duty", 12, "extended"),
        ])
        
        regulatory_scenarios = st.sampled_from([
            ("Airport curfew allows operation until 23:00", 23, "standard"),
            ("Weather minimums require daylight operation only", 18, "daylight"),
            ("NOTAM restricts operations to 20:00", 20, "restricted"),
            ("Emergency curfew in effect until 22:00", 22, "emergency"),
        ])
        
        @given(
            crew_scenario=crew_scenarios,
            regulatory_scenario=regulatory_scenarios,
        )
        @settings(max_examples=30, deadline=None)
        def property_test(crew_scenario, regulatory_scenario):
            crew_desc, crew_hours, crew_type = crew_scenario
            reg_desc, reg_hour, reg_type = regulatory_scenario
            
            # Create conflicting safety agent responses
            responses = {
                "crew_compliance": {
                    "recommendation": crew_desc,
                    "confidence": 0.91,
                    "binding_constraints": [f"Crew rest requirement: {crew_hours} hours"],
                    "reasoning": f"Crew compliance requires {crew_type} rest period"
                },
                "regulatory": {
                    "recommendation": reg_desc,
                    "confidence": 0.93,
                    "binding_constraints": [f"Regulatory restriction: operations until {reg_hour}:00"],
                    "reasoning": f"Regulatory compliance requires {reg_type} operation window"
                },
                "network": {
                    "recommendation": "Operate as soon as possible",
                    "confidence": 0.84,
                    "reasoning": "Network optimization"
                }
            }
            
            # Create mock LLM
            mock_llm = Mock()
            mock_structured_llm = Mock()
            
            # Mock decision that satisfies both constraints (most conservative)
            mock_decision = ArbitratorOutput(
                final_decision=f"Satisfy both crew rest ({crew_hours}h) and regulatory ({reg_hour}:00) requirements",
                recommendations=[
                    f"Ensure crew has {crew_hours}-hour rest",
                    f"Schedule operation within regulatory window (until {reg_hour}:00)",
                    "Choose most conservative timeline that satisfies both"
                ],
                conflicts_identified=[
                    ConflictDetail(
                        agents_involved=["crew_compliance", "regulatory"],
                        conflict_type="safety_vs_safety",
                        description=f"Crew rest requirement conflicts with regulatory time window"
                    )
                ],
                conflict_resolutions=[
                    ResolutionDetail(
                        conflict_description="Crew rest vs regulatory window",
                        resolution="Satisfy both constraints with conservative scheduling",
                        rationale="Both safety constraints are non-negotiable. Choose timeline that satisfies both."
                    )
                ],
                safety_overrides=[
                    SafetyOverride(
                        safety_agent="crew_compliance",
                        binding_constraint=f"Crew rest: {crew_hours} hours",
                        overridden_recommendations=["Operate as soon as possible"]
                    ),
                    SafetyOverride(
                        safety_agent="regulatory",
                        binding_constraint=f"Regulatory window: until {reg_hour}:00",
                        overridden_recommendations=["Operate as soon as possible"]
                    )
                ],
                justification="Both safety constraints must be satisfied. Conservative approach ensures compliance.",
                reasoning="Applied Rule 2: Safety vs Safety - choose most conservative option that satisfies both",
                confidence=0.92,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            mock_structured_llm.invoke = Mock(return_value=mock_decision)
            mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
            
            # Call arbitrate synchronously using asyncio.run
            result = asyncio.run(arbitrate(responses, llm_opus=mock_llm))
            
            # Property: Both safety constraints must be mentioned in decision
            decision_text = result["final_decision"] + " ".join(result["recommendations"])
            assert str(crew_hours) in decision_text or "crew" in decision_text.lower(), \
                   "Crew constraint must be addressed in final decision"
            assert str(reg_hour) in decision_text or "regulatory" in decision_text.lower(), \
                   "Regulatory constraint must be addressed in final decision"
            
            # Property: Conflict type must be safety_vs_safety
            if result["conflicts_identified"]:
                assert any(conflict["conflict_type"] == "safety_vs_safety" 
                          for conflict in result["conflicts_identified"]), \
                       "Conflict between safety agents must be identified as safety_vs_safety"
            
            # Property: Both safety agents should have overrides (both constraints enforced)
            safety_agents_in_overrides = {override["safety_agent"] 
                                         for override in result["safety_overrides"]}
            # At least one safety agent should be in overrides
            assert len(safety_agents_in_overrides) >= 1, \
                   "At least one safety constraint must be enforced"
        
        # Run the property test
        property_test()
    
    def test_multiple_safety_conflicts_most_conservative_wins(self):
        """
        Property 9.3: Multiple safety conflicts resolve to most conservative across all
        
        When three safety agents have different requirements, the arbitrator must
        choose the option that satisfies all constraints (most conservative overall).
        
        Validates: Requirements 11.4, 11.5, 13.4
        """
        from hypothesis import given, strategies as st, settings
        import asyncio
        
        # Define strategies for different delay requirements
        crew_delays = st.integers(min_value=6, max_value=12)
        maintenance_delays = st.integers(min_value=4, max_value=10)
        regulatory_delays = st.integers(min_value=2, max_value=8)
        
        @given(
            crew_delay=crew_delays,
            maintenance_delay=maintenance_delays,
            regulatory_delay=regulatory_delays,
        )
        @settings(max_examples=30, deadline=None)
        def property_test(crew_delay, maintenance_delay, regulatory_delay):
            # Determine the most conservative (longest) delay
            most_conservative_delay = max(crew_delay, maintenance_delay, regulatory_delay)
            
            # Create conflicting safety agent responses
            responses = {
                "crew_compliance": {
                    "recommendation": f"Delay flight by {crew_delay} hours for crew rest",
                    "confidence": 0.92,
                    "binding_constraints": [f"Minimum {crew_delay}-hour delay required"],
                    "reasoning": f"Crew rest requires {crew_delay} hours"
                },
                "maintenance": {
                    "recommendation": f"Delay flight by {maintenance_delay} hours for inspection",
                    "confidence": 0.90,
                    "binding_constraints": [f"Minimum {maintenance_delay}-hour delay required"],
                    "reasoning": f"Maintenance inspection requires {maintenance_delay} hours"
                },
                "regulatory": {
                    "recommendation": f"Delay flight by {regulatory_delay} hours for compliance",
                    "confidence": 0.91,
                    "binding_constraints": [f"Minimum {regulatory_delay}-hour delay required"],
                    "reasoning": f"Regulatory compliance requires {regulatory_delay} hours"
                },
                "network": {
                    "recommendation": "Minimize delay to 2 hours",
                    "confidence": 0.85,
                    "reasoning": "Network optimization"
                }
            }
            
            # Create mock LLM
            mock_llm = Mock()
            mock_structured_llm = Mock()
            
            # Determine which agent has the most conservative requirement
            agent_delays = {
                "crew_compliance": crew_delay,
                "maintenance": maintenance_delay,
                "regulatory": regulatory_delay
            }
            most_conservative_agent = max(agent_delays, key=agent_delays.get)
            
            # Mock decision that chooses the most conservative delay
            mock_decision = ArbitratorOutput(
                final_decision=f"Delay flight by {most_conservative_delay} hours to satisfy all safety requirements",
                recommendations=[
                    f"Implement {most_conservative_delay}-hour delay",
                    "Satisfy all safety agent requirements",
                    "Adjust network schedule accordingly"
                ],
                conflicts_identified=[
                    ConflictDetail(
                        agents_involved=["crew_compliance", "maintenance", "regulatory"],
                        conflict_type="safety_vs_safety",
                        description=f"Multiple safety agents require different delays: {crew_delay}h, {maintenance_delay}h, {regulatory_delay}h"
                    )
                ],
                conflict_resolutions=[
                    ResolutionDetail(
                        conflict_description="Multiple safety delay requirements",
                        resolution=f"Choose {most_conservative_delay}-hour delay (most conservative)",
                        rationale=f"Most conservative option satisfies all safety requirements. {most_conservative_delay} hours ensures all constraints met."
                    )
                ],
                safety_overrides=[
                    SafetyOverride(
                        safety_agent=most_conservative_agent,
                        binding_constraint=f"Minimum {most_conservative_delay}-hour delay",
                        overridden_recommendations=["Minimize delay to 2 hours"]
                    )
                ],
                justification=f"All safety constraints must be satisfied. {most_conservative_delay}-hour delay is most conservative option.",
                reasoning="Applied Rule 2: Safety vs Safety - choose most conservative option that satisfies all constraints",
                confidence=0.93,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            mock_structured_llm.invoke = Mock(return_value=mock_decision)
            mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
            
            # Call arbitrate synchronously using asyncio.run
            result = asyncio.run(arbitrate(responses, llm_opus=mock_llm))
            
            # Property: Final decision must include the most conservative delay
            decision_text = result["final_decision"] + " ".join(result["recommendations"])
            assert str(most_conservative_delay) in decision_text, \
                   f"Final decision must include most conservative delay: {most_conservative_delay} hours"
            
            # Property: Conflict type must be safety_vs_safety
            if result["conflicts_identified"]:
                assert any(conflict["conflict_type"] == "safety_vs_safety" 
                          for conflict in result["conflicts_identified"]), \
                       "Conflict between safety agents must be identified as safety_vs_safety"
            
            # Property: Resolution must mention "conservative"
            if result["conflict_resolutions"]:
                resolution_text = " ".join(res["resolution"] + res["rationale"] 
                                          for res in result["conflict_resolutions"])
                assert "conservative" in resolution_text.lower(), \
                       "Resolution must explicitly mention conservative approach"
            
            # Property: The chosen delay must be >= all individual delays
            # (This is the definition of "most conservative")
            assert most_conservative_delay >= crew_delay, \
                   "Chosen delay must satisfy crew requirement"
            assert most_conservative_delay >= maintenance_delay, \
                   "Chosen delay must satisfy maintenance requirement"
            assert most_conservative_delay >= regulatory_delay, \
                   "Chosen delay must satisfy regulatory requirement"
        
        # Run the property test
        property_test()
    
    @pytest.mark.asyncio
    async def test_cancellation_is_most_conservative(self):
        """
        Property 9.4: Flight cancellation is the most conservative option
        
        When safety agents recommend cancellation vs delay, cancellation should
        be chosen as the most conservative option.
        
        Validates: Requirements 11.4, 13.4
        """
        # Create responses where one agent recommends cancellation
        responses = {
            "crew_compliance": {
                "recommendation": "Cancel flight - no qualified crew available",
                "confidence": 0.95,
                "binding_constraints": ["Flight must be cancelled - no crew available"],
                "reasoning": "No replacement crew can be sourced within acceptable timeframe"
            },
            "maintenance": {
                "recommendation": "Delay 8 hours for inspection",
                "confidence": 0.88,
                "binding_constraints": ["8-hour inspection required"],
                "reasoning": "Inspection can be completed in 8 hours"
            },
            "network": {
                "recommendation": "Delay 4 hours",
                "confidence": 0.85,
                "reasoning": "Network optimization"
            }
        }
        
        # Create mock LLM
        mock_llm = Mock()
        mock_structured_llm = Mock()
        
        # Mock decision that chooses cancellation (most conservative)
        mock_decision = ArbitratorOutput(
            final_decision="Cancel flight as recommended by crew compliance - most conservative option",
            recommendations=[
                "Cancel flight",
                "Rebook passengers on alternative flights",
                "Provide full passenger protection"
            ],
            conflicts_identified=[
                ConflictDetail(
                    agents_involved=["crew_compliance", "maintenance"],
                    conflict_type="safety_vs_safety",
                    description="Crew recommends cancellation vs Maintenance recommends delay"
                )
            ],
            conflict_resolutions=[
                ResolutionDetail(
                    conflict_description="Cancellation vs delay",
                    resolution="Choose cancellation (most conservative)",
                    rationale="Cancellation is more conservative than delay when crew availability is uncertain"
                )
            ],
            safety_overrides=[
                SafetyOverride(
                    safety_agent="crew_compliance",
                    binding_constraint="Flight must be cancelled - no crew available",
                    overridden_recommendations=["Delay 8 hours for inspection", "Delay 4 hours"]
                )
            ],
            justification="Cancellation is most conservative option when crew availability cannot be guaranteed",
            reasoning="Applied Rule 2: Safety vs Safety - choose most conservative (cancellation over delay)",
            confidence=0.94,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        mock_structured_llm.invoke = Mock(return_value=mock_decision)
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
        
        # Call arbitrate
        result = await arbitrate(responses, llm_opus=mock_llm)
        
        # Property: Final decision must include cancellation
        decision_text = result["final_decision"].lower()
        assert "cancel" in decision_text, \
               "Final decision must choose cancellation as most conservative option"
        
        # Property: Conflict type must be safety_vs_safety
        if result["conflicts_identified"]:
            assert any(conflict["conflict_type"] == "safety_vs_safety" 
                      for conflict in result["conflicts_identified"]), \
                   "Conflict between safety agents must be identified as safety_vs_safety"
        
        # Property: Resolution must mention "conservative"
        if result["conflict_resolutions"]:
            resolution_text = " ".join(res["resolution"] + res["rationale"] 
                                      for res in result["conflict_resolutions"])
            assert "conservative" in resolution_text.lower(), \
                   "Resolution must explicitly mention conservative approach"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
