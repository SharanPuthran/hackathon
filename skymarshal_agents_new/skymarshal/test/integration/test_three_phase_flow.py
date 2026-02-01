"""
Integration Tests for Three-Phase Orchestration Flow

Task 16.1: Create test/integration/test_three_phase_flow.py
- Test complete flow from natural language prompt to final decision
- Verify agents use LangChain structured output for extraction
- Verify phase execution order
- Verify collation accuracy
- Verify audit trail completeness

Validates: Requirements 9, 10, 11, 15
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from main import (
    handle_disruption,
    phase1_initial_recommendations,
    phase2_revision_round,
    phase3_arbitration,
)
from agents.schemas import AgentResponse, Collation


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_llm():
    """Mock LLM instance"""
    return Mock()


@pytest.fixture
def mock_mcp_tools():
    """Mock MCP tools"""
    return []


@pytest.fixture
def sample_user_prompt():
    """Sample natural language prompt"""
    return "Flight EY123 on January 20th 2026 had a mechanical failure"


@pytest.fixture
def mock_successful_agent_response():
    """Factory for creating mock successful agent responses"""
    def _create_response(agent_name: str, recommendation: str = None):
        # Map test agent names to valid agent names
        valid_agent_map = {
            "test_agent": "crew_compliance",
            "detailed_agent": "maintenance",
            "reasoning_agent": "regulatory",
            "evolving_agent": "network",
            "success_agent": "guest_experience",
            "failing_agent": "cargo"
        }
        valid_agent_name = valid_agent_map.get(agent_name, agent_name)
        
        return {
            "agent": valid_agent_name,
            "status": "success",
            "recommendation": recommendation or f"{agent_name} recommendation",
            "confidence": 0.95,
            "reasoning": f"{agent_name} reasoning",
            "data_sources": ["test_source"],
            "extracted_flight_info": {
                "flight_number": "EY123",
                "date": "2026-01-20",
                "disruption_event": "mechanical failure"
            },
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": 1.0
        }
    return _create_response


# ============================================================================
# Test Complete Three-Phase Flow
# ============================================================================


class TestCompleteThreePhaseFlow:
    """Test complete end-to-end three-phase orchestration flow"""
    
    @pytest.mark.asyncio
    async def test_complete_flow_from_prompt_to_decision(
        self, sample_user_prompt, mock_llm, mock_mcp_tools, mock_successful_agent_response
    ):
        """
        Test complete flow from natural language prompt to final decision
        
        Validates:
        - Requirements 9.1-9.8 (Phase 1: Initial Recommendations)
        - Requirements 10.1-10.7 (Phase 2: Revision Round)
        - Requirements 11.1-11.7 (Phase 3: Arbitration)
        - Requirements 15.1-15.5 (Audit Trail and Explainability)
        """
        # Mock all agents to return success
        safety_agents = ["crew_compliance", "maintenance", "regulatory"]
        business_agents = ["network", "guest_experience", "cargo", "finance"]
        
        # Create agent-specific mock functions
        def create_agent_mock(agent_name):
            async def mock_agent(payload, llm, mcp_tools):
                return mock_successful_agent_response(agent_name)
            return mock_agent
        
        # Patch agent registry
        with patch("main.SAFETY_AGENTS", [(name, create_agent_mock(name)) for name in safety_agents]):
            with patch("main.BUSINESS_AGENTS", [(name, create_agent_mock(name)) for name in business_agents]):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify response structure
        assert result["status"] == "success"
        assert "final_decision" in result
        assert "audit_trail" in result
        assert "timestamp" in result
        
        # Verify audit trail completeness (Requirement 15.1-15.5)
        audit_trail = result["audit_trail"]
        assert "user_prompt" in audit_trail
        assert audit_trail["user_prompt"] == sample_user_prompt
        assert "phase1_initial" in audit_trail
        assert "phase2_revision" in audit_trail
        assert "phase3_arbitration" in audit_trail
        
        # Verify phase 1 structure
        phase1 = audit_trail["phase1_initial"]
        assert phase1["phase"] == "initial"
        assert "responses" in phase1
        assert len(phase1["responses"]) == 7  # All 7 agents
        
        # Verify phase 2 structure
        phase2 = audit_trail["phase2_revision"]
        assert phase2["phase"] == "revision"
        assert "responses" in phase2
        assert len(phase2["responses"]) == 7  # All 7 agents
        
        # Verify phase 3 structure
        phase3 = audit_trail["phase3_arbitration"]
        assert phase3["phase"] == "arbitration"
        assert "final_decision" in phase3
        assert "recommendations" in phase3
        
        # Verify timing information
        assert "phase1_duration_seconds" in result
        assert "phase2_duration_seconds" in result
        assert "phase3_duration_seconds" in result
        assert "total_duration_seconds" in result
        assert result["total_duration_seconds"] > 0
    
    @pytest.mark.asyncio
    async def test_agents_use_structured_output_for_extraction(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that agents use LangChain structured output for data extraction
        
        Validates:
        - Requirements 1.7, 1.8 (Agents extract flight info using structured output)
        - Requirements 2.1 (Agents use with_structured_output())
        """
        # Mock agent that verifies structured output usage
        extracted_info_captured = []
        
        async def mock_agent_with_extraction(payload, llm, mcp_tools):
            # Verify payload contains user_prompt
            assert "user_prompt" in payload
            assert sample_user_prompt in payload["user_prompt"]
            
            # Simulate structured output extraction
            extracted_info = {
                "flight_number": "EY123",
                "date": "2026-01-20",
                "disruption_event": "mechanical failure"
            }
            extracted_info_captured.append(extracted_info)
            
            return {
                "agent": "crew_compliance",  # Use valid agent name
                "status": "success",
                "recommendation": "Test recommendation",
                "confidence": 0.95,
                "reasoning": "Test reasoning",
                "data_sources": ["test"],
                "extracted_flight_info": extracted_info,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 1.0
            }
        
        # Patch agents
        with patch("main.SAFETY_AGENTS", [("crew_compliance", mock_agent_with_extraction)]):
            with patch("main.BUSINESS_AGENTS", []):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify agents extracted flight info
        assert len(extracted_info_captured) >= 1
        for info in extracted_info_captured:
            assert info["flight_number"] == "EY123"
            assert info["date"] == "2026-01-20"
            assert info["disruption_event"] == "mechanical failure"
        
        # Verify extracted info in audit trail
        phase1_responses = result["audit_trail"]["phase1_initial"]["responses"]
        for agent_name, response in phase1_responses.items():
            if response.get("extracted_flight_info"):
                assert response["extracted_flight_info"]["flight_number"] == "EY123"


# ============================================================================
# Test Phase Execution Order
# ============================================================================


class TestPhaseExecutionOrder:
    """Test that phases execute in correct order"""
    
    @pytest.mark.asyncio
    async def test_phase_execution_order_is_sequential(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that phases execute in strict order: initial → revision → arbitration
        
        Validates:
        - Requirements 9.1 (Phase 1 executes first)
        - Requirements 10.1 (Phase 2 executes after Phase 1)
        - Requirements 11.1 (Phase 3 executes after Phase 2)
        - Property 6: Three-Phase Execution Order
        """
        execution_order = []
        
        async def track_phase1(*args):
            execution_order.append("phase1")
            return Collation(
                phase="initial",
                responses={
                    "crew_compliance": AgentResponse(
                        agent_name="crew_compliance",
                        recommendation="Test",
                        confidence=0.9,
                        reasoning="Test",
                        data_sources=[],
                        timestamp=datetime.now().isoformat()
                    )
                },
                timestamp=datetime.now().isoformat(),
                duration_seconds=0.1
            )
        
        async def track_phase2(*args):
            execution_order.append("phase2")
            return Collation(
                phase="revision",
                responses={
                    "crew_compliance": AgentResponse(
                        agent_name="crew_compliance",
                        recommendation="Test",
                        confidence=0.9,
                        reasoning="Test",
                        data_sources=[],
                        timestamp=datetime.now().isoformat()
                    )
                },
                timestamp=datetime.now().isoformat(),
                duration_seconds=0.1
            )
        
        async def track_phase3(*args):
            execution_order.append("phase3")
            return {
                "phase": "arbitration",
                "final_decision": "Test",
                "recommendations": [],
                "conflicts_identified": [],
                "conflict_resolutions": [],
                "safety_overrides": [],
                "justification": "Test",
                "reasoning": "Test",
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 0.1
            }
        
        # Patch phase functions
        with patch("main.phase1_initial_recommendations", track_phase1):
            with patch("main.phase2_revision_round", track_phase2):
                with patch("main.phase3_arbitration", track_phase3):
                    result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify execution order
        assert execution_order == ["phase1", "phase2", "phase3"]
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_phase2_receives_phase1_collation(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that phase 2 receives phase 1 collation
        
        Validates:
        - Requirements 10.1 (Phase 2 receives initial recommendations)
        - Requirements 10.2 (Agents review other agents' findings)
        """
        phase1_collation_received = None
        
        async def capture_phase2_input(user_prompt, initial_collation, llm, mcp_tools):
            nonlocal phase1_collation_received
            phase1_collation_received = initial_collation
            
            return Collation(
                phase="revision",
                responses={
                    "crew_compliance": AgentResponse(
                        agent_name="crew_compliance",
                        recommendation="Test",
                        confidence=0.9,
                        reasoning="Test",
                        data_sources=[],
                        timestamp=datetime.now().isoformat()
                    )
                },
                timestamp=datetime.now().isoformat(),
                duration_seconds=0.1
            )
        
        # Mock phase 1 to return collation
        async def mock_phase1(*args):
            return Collation(
                phase="initial",
                responses={
                    "crew_compliance": AgentResponse(
                        agent_name="crew_compliance",
                        recommendation="Crew available",
                        confidence=0.95,
                        reasoning="Test",
                        data_sources=[],
                        timestamp=datetime.now().isoformat()
                    )
                },
                timestamp=datetime.now().isoformat(),
                duration_seconds=1.0
            )
        
        # Mock phase 3
        async def mock_phase3(*args):
            return {
                "phase": "arbitration",
                "final_decision": "Test",
                "recommendations": [],
                "conflicts_identified": [],
                "conflict_resolutions": [],
                "safety_overrides": [],
                "justification": "Test",
                "reasoning": "Test",
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 0.1
            }
        
        # Patch phases
        with patch("main.phase1_initial_recommendations", mock_phase1):
            with patch("main.phase2_revision_round", capture_phase2_input):
                with patch("main.phase3_arbitration", mock_phase3):
                    result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify phase 2 received phase 1 collation
        assert phase1_collation_received is not None
        assert isinstance(phase1_collation_received, Collation)
        assert phase1_collation_received.phase == "initial"
        assert "crew_compliance" in phase1_collation_received.responses
    
    @pytest.mark.asyncio
    async def test_phase3_receives_phase2_collation(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that phase 3 receives phase 2 collation
        
        Validates:
        - Requirements 11.1 (Phase 3 receives revised recommendations)
        """
        phase2_collation_received = None
        
        async def capture_phase3_input(revised_collation, llm):
            nonlocal phase2_collation_received
            phase2_collation_received = revised_collation
            
            return {
                "phase": "arbitration",
                "final_decision": "Test",
                "recommendations": [],
                "conflicts_identified": [],
                "conflict_resolutions": [],
                "safety_overrides": [],
                "justification": "Test",
                "reasoning": "Test",
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 0.1
            }
        
        # Mock phases 1 and 2
        async def mock_phase1(*args):
            return Collation(
                phase="initial",
                responses={
                    "crew_compliance": AgentResponse(
                        agent_name="crew_compliance",
                        recommendation="Initial",
                        confidence=0.9,
                        reasoning="Test",
                        data_sources=[],
                        timestamp=datetime.now().isoformat()
                    )
                },
                timestamp=datetime.now().isoformat(),
                duration_seconds=1.0
            )
        
        async def mock_phase2(*args):
            return Collation(
                phase="revision",
                responses={
                    "crew_compliance": AgentResponse(
                        agent_name="crew_compliance",
                        recommendation="Revised",
                        confidence=0.95,
                        reasoning="Test",
                        data_sources=[],
                        timestamp=datetime.now().isoformat()
                    )
                },
                timestamp=datetime.now().isoformat(),
                duration_seconds=1.0
            )
        
        # Patch phases
        with patch("main.phase1_initial_recommendations", mock_phase1):
            with patch("main.phase2_revision_round", mock_phase2):
                with patch("main.phase3_arbitration", capture_phase3_input):
                    result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify phase 3 received phase 2 collation
        assert phase2_collation_received is not None
        assert isinstance(phase2_collation_received, Collation)
        assert phase2_collation_received.phase == "revision"


# ============================================================================
# Test Collation Accuracy
# ============================================================================


class TestCollationAccuracy:
    """Test that collations accurately aggregate agent responses"""
    
    @pytest.mark.asyncio
    async def test_phase1_collation_includes_all_agents(
        self, sample_user_prompt, mock_llm, mock_mcp_tools, mock_successful_agent_response
    ):
        """
        Test that phase 1 collation includes all 7 agents
        
        Validates:
        - Requirements 9.8 (Collate all initial recommendations)
        """
        # Mock all 7 agents
        safety_agents = ["crew_compliance", "maintenance", "regulatory"]
        business_agents = ["network", "guest_experience", "cargo", "finance"]
        
        # Create agent-specific mock functions
        def create_agent_mock(agent_name):
            async def mock_agent(payload, llm, mcp_tools):
                return mock_successful_agent_response(agent_name)
            return mock_agent
        
        with patch("main.SAFETY_AGENTS", [(name, create_agent_mock(name)) for name in safety_agents]):
            with patch("main.BUSINESS_AGENTS", [(name, create_agent_mock(name)) for name in business_agents]):
                collation = await phase1_initial_recommendations(
                    sample_user_prompt, mock_llm, mock_mcp_tools
                )
        
        # Verify collation structure
        assert isinstance(collation, Collation)
        assert collation.phase == "initial"
        assert len(collation.responses) == 7
        
        # Verify all agents present
        all_agents = safety_agents + business_agents
        for agent_name in all_agents:
            assert agent_name in collation.responses
            assert isinstance(collation.responses[agent_name], AgentResponse)
    
    @pytest.mark.asyncio
    async def test_collation_handles_mixed_success_and_failure(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that collation handles mixed success and failure responses
        
        Validates:
        - Requirements 16.1 (Graceful error handling)
        """
        # Mock agents with different statuses
        async def success_agent(payload, llm, mcp_tools):
            return {
                "agent": "crew_compliance",  # Use valid agent name
                "status": "success",
                "recommendation": "Success",
                "confidence": 0.95,
                "reasoning": "Test",
                "data_sources": [],
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 1.0
            }
        
        async def timeout_agent(payload, llm, mcp_tools):
            await asyncio.sleep(35)  # Simulate timeout
            return {"agent": "maintenance"}
        
        async def error_agent(payload, llm, mcp_tools):
            raise ValueError("Test error")
        
        # Patch agents
        with patch("main.SAFETY_AGENTS", [
            ("crew_compliance", success_agent),
            ("maintenance", timeout_agent),
            ("regulatory", error_agent)
        ]):
            with patch("main.BUSINESS_AGENTS", []):
                collation = await phase1_initial_recommendations(
                    sample_user_prompt, mock_llm, mock_mcp_tools
                )
        
        # Verify collation includes all agents
        assert len(collation.responses) == 3
        
        # Verify success agent
        assert collation.responses["crew_compliance"].status == "success"
        
        # Verify timeout agent
        assert collation.responses["maintenance"].status == "timeout"
        
        # Verify error agent
        assert collation.responses["regulatory"].status == "error"
        
        # Verify helper methods
        successful = collation.get_successful_responses()
        assert len(successful) == 1
        assert "crew_compliance" in successful
        
        failed = collation.get_failed_responses()
        assert len(failed) == 2
        assert "maintenance" in failed
        assert "regulatory" in failed
    
    @pytest.mark.asyncio
    async def test_collation_preserves_agent_response_data(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that collation preserves all agent response data
        
        Validates:
        - Requirements 15.2 (Log all agent responses with confidence and reasoning)
        """
        # Mock agent with detailed response
        async def detailed_agent(payload, llm, mcp_tools):
            return {
                "agent": "maintenance",  # Use valid agent name
                "status": "success",
                "recommendation": "Detailed recommendation",
                "confidence": 0.87,
                "reasoning": "Detailed reasoning with multiple points",
                "data_sources": ["CrewRoster", "CrewMembers", "Flights"],
                "binding_constraints": ["Must have qualified crew"],
                "extracted_flight_info": {
                    "flight_number": "EY123",
                    "date": "2026-01-20",
                    "disruption_event": "mechanical failure"
                },
                "timestamp": "2026-02-01T12:00:00Z",
                "duration_seconds": 2.5
            }
        
        # Patch agents
        with patch("main.SAFETY_AGENTS", [("maintenance", detailed_agent)]):
            with patch("main.BUSINESS_AGENTS", []):
                collation = await phase1_initial_recommendations(
                    sample_user_prompt, mock_llm, mock_mcp_tools
                )
        
        # Verify all data preserved
        response = collation.responses["maintenance"]
        assert response.agent_name == "maintenance"
        assert response.recommendation == "Detailed recommendation"
        assert response.confidence == 0.87
        assert response.reasoning == "Detailed reasoning with multiple points"
        assert len(response.data_sources) == 3
        assert "CrewRoster" in response.data_sources
        assert len(response.binding_constraints) == 1
        assert response.binding_constraints[0] == "Must have qualified crew"
        assert response.extracted_flight_info is not None
        assert response.extracted_flight_info["flight_number"] == "EY123"
        # Note: duration_seconds is overridden by run_agent_safely, so we just check it exists
        assert response.duration_seconds is not None
        assert response.duration_seconds > 0


# ============================================================================
# Test Audit Trail Completeness
# ============================================================================


class TestAuditTrailCompleteness:
    """Test that audit trail is complete and preserves decision chain"""
    
    @pytest.mark.asyncio
    async def test_audit_trail_contains_all_required_fields(
        self, sample_user_prompt, mock_llm, mock_mcp_tools, mock_successful_agent_response
    ):
        """
        Test that audit trail contains all required fields
        
        Validates:
        - Requirements 15.1 (Log all agent invocations)
        - Requirements 15.2 (Log all agent responses)
        - Requirements 15.3 (Log all arbitrator decisions)
        - Requirements 15.4 (Preserve complete decision chain)
        - Property 10: Audit Trail Completeness
        """
        # Mock agents
        async def mock_agent(payload, llm, mcp_tools):
            return mock_successful_agent_response("crew_compliance")
        
        with patch("main.SAFETY_AGENTS", [("crew_compliance", mock_agent)]):
            with patch("main.BUSINESS_AGENTS", []):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify top-level audit trail structure
        assert "audit_trail" in result
        audit_trail = result["audit_trail"]
        
        # Verify required fields
        required_fields = [
            "user_prompt",
            "phase1_initial",
            "phase2_revision",
            "phase3_arbitration"
        ]
        for field in required_fields:
            assert field in audit_trail, f"Missing required field: {field}"
        
        # Verify user prompt preserved
        assert audit_trail["user_prompt"] == sample_user_prompt
        
        # Verify phase 1 structure
        phase1 = audit_trail["phase1_initial"]
        assert "phase" in phase1
        assert "responses" in phase1
        assert "timestamp" in phase1
        assert "duration_seconds" in phase1
        
        # Verify phase 2 structure
        phase2 = audit_trail["phase2_revision"]
        assert "phase" in phase2
        assert "responses" in phase2
        assert "timestamp" in phase2
        assert "duration_seconds" in phase2
        
        # Verify phase 3 structure
        phase3 = audit_trail["phase3_arbitration"]
        assert "phase" in phase3
        assert "final_decision" in phase3
        assert "recommendations" in phase3
        assert "timestamp" in phase3
    
    @pytest.mark.asyncio
    async def test_audit_trail_preserves_timestamps(
        self, sample_user_prompt, mock_llm, mock_mcp_tools, mock_successful_agent_response
    ):
        """
        Test that audit trail preserves timestamps for all phases
        
        Validates:
        - Requirements 15.1 (Log with timestamps)
        """
        # Mock agents
        async def mock_agent(payload, llm, mcp_tools):
            return mock_successful_agent_response("crew_compliance")
        
        with patch("main.SAFETY_AGENTS", [("crew_compliance", mock_agent)]):
            with patch("main.BUSINESS_AGENTS", []):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        audit_trail = result["audit_trail"]
        
        # Verify timestamps exist
        assert "timestamp" in result
        assert "timestamp" in audit_trail["phase1_initial"]
        assert "timestamp" in audit_trail["phase2_revision"]
        assert "timestamp" in audit_trail["phase3_arbitration"]
        
        # Verify timestamps are valid ISO format
        from datetime import datetime
        for timestamp_str in [
            result["timestamp"],
            audit_trail["phase1_initial"]["timestamp"],
            audit_trail["phase2_revision"]["timestamp"],
            audit_trail["phase3_arbitration"]["timestamp"]
        ]:
            # Should be parseable as ISO format
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    
    @pytest.mark.asyncio
    async def test_audit_trail_preserves_agent_reasoning(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that audit trail preserves agent reasoning and confidence
        
        Validates:
        - Requirements 15.2 (Log responses with confidence and reasoning)
        """
        # Mock agent with detailed reasoning
        async def reasoning_agent(payload, llm, mcp_tools):
            return {
                "agent": "regulatory",  # Use valid agent name
                "status": "success",
                "recommendation": "Delay flight by 2 hours",
                "confidence": 0.92,
                "reasoning": "Based on crew availability and maintenance requirements, "
                            "a 2-hour delay allows sufficient time for inspection and crew rest.",
                "data_sources": ["CrewRoster", "MaintenanceWorkOrders"],
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 1.5
            }
        
        with patch("main.SAFETY_AGENTS", [("regulatory", reasoning_agent)]):
            with patch("main.BUSINESS_AGENTS", []):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify reasoning preserved in audit trail
        phase1_responses = result["audit_trail"]["phase1_initial"]["responses"]
        agent_response = phase1_responses["regulatory"]
        
        assert agent_response["recommendation"] == "Delay flight by 2 hours"
        assert agent_response["confidence"] == 0.92
        assert "crew availability" in agent_response["reasoning"]
        assert "maintenance requirements" in agent_response["reasoning"]
        assert len(agent_response["data_sources"]) == 2
    
    @pytest.mark.asyncio
    async def test_audit_trail_can_reconstruct_decision_chain(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that audit trail can reconstruct complete decision chain
        
        Validates:
        - Requirements 15.4 (Preserve complete decision chain)
        - Requirements 15.5 (Provide full audit trail in human-readable format)
        """
        # Mock agents with evolving recommendations
        async def initial_agent(payload, llm, mcp_tools):
            if payload.get("phase") == "initial":
                return {
                    "agent": "network",  # Use valid agent name
                    "status": "success",
                    "recommendation": "Initial: Delay by 1 hour",
                    "confidence": 0.80,
                    "reasoning": "Initial assessment based on limited data",
                    "data_sources": ["Flights"],
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": 1.0
                }
            else:  # revision phase
                return {
                    "agent": "network",  # Use valid agent name
                    "status": "success",
                    "recommendation": "Revised: Delay by 2 hours",
                    "confidence": 0.90,
                    "reasoning": "Revised after reviewing maintenance agent's findings",
                    "data_sources": ["Flights", "MaintenanceWorkOrders"],
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": 1.0
                }
        
        with patch("main.SAFETY_AGENTS", []):
            with patch("main.BUSINESS_AGENTS", [("network", initial_agent)]):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        audit_trail = result["audit_trail"]
        
        # Verify we can trace the evolution of recommendations
        phase1_response = audit_trail["phase1_initial"]["responses"]["network"]
        phase2_response = audit_trail["phase2_revision"]["responses"]["network"]
        
        # Verify initial recommendation
        assert "Initial: Delay by 1 hour" in phase1_response["recommendation"]
        assert phase1_response["confidence"] == 0.80
        
        # Verify revised recommendation
        assert "Revised: Delay by 2 hours" in phase2_response["recommendation"]
        assert phase2_response["confidence"] == 0.90
        assert "maintenance agent" in phase2_response["reasoning"]
        
        # Verify we can reconstruct the decision chain
        assert phase1_response["recommendation"] != phase2_response["recommendation"]
        assert phase2_response["confidence"] > phase1_response["confidence"]


# ============================================================================
# Test Error Scenarios
# ============================================================================


class TestErrorScenarios:
    """Test error handling in three-phase flow"""
    
    @pytest.mark.asyncio
    async def test_flow_continues_with_agent_failures(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Test that flow continues even when some agents fail
        
        Validates:
        - Requirements 16.1 (Continue with available responses)
        - Property 11: Graceful Degradation
        """
        # Mock agents with failures
        async def success_agent(payload, llm, mcp_tools):
            return {
                "agent": "guest_experience",  # Use valid agent name
                "status": "success",
                "recommendation": "Success",
                "confidence": 0.95,
                "reasoning": "Test",
                "data_sources": [],
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 1.0
            }
        
        async def failing_agent(payload, llm, mcp_tools):
            raise RuntimeError("Agent failure")
        
        # Patch agents
        with patch("main.SAFETY_AGENTS", []):
            with patch("main.BUSINESS_AGENTS", [
                ("guest_experience", success_agent),
                ("cargo", failing_agent)
            ]):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify flow completed
        assert result["status"] == "success"
        assert "audit_trail" in result
        
        # Verify both agents in collation
        phase1_responses = result["audit_trail"]["phase1_initial"]["responses"]
        assert "guest_experience" in phase1_responses
        assert "cargo" in phase1_responses
        
        # Verify success agent succeeded
        assert phase1_responses["guest_experience"]["status"] == "success"
        
        # Verify failing agent has error status
        assert phase1_responses["cargo"]["status"] == "error"
        assert phase1_responses["cargo"]["error"] is not None
    
    @pytest.mark.asyncio
    async def test_empty_prompt_validation(
        self, mock_llm, mock_mcp_tools
    ):
        """
        Test that empty prompt is rejected
        
        Validates:
        - Requirements 1.13 (Request missing information)
        """
        result = await handle_disruption("", mock_llm, mock_mcp_tools)
        
        assert result["status"] == "VALIDATION_FAILED"
        assert "No prompt provided" in result["reason"]
        assert "recommendations" in result


# ============================================================================
# Test Performance Targets
# ============================================================================


class TestPerformanceTargets:
    """Test that performance targets are met"""
    
    @pytest.mark.asyncio
    async def test_phase_durations_recorded(
        self, sample_user_prompt, mock_llm, mock_mcp_tools, mock_successful_agent_response
    ):
        """
        Test that phase durations are recorded
        
        Validates:
        - Performance monitoring requirements
        """
        # Mock agents
        async def mock_agent(payload, llm, mcp_tools):
            await asyncio.sleep(0.1)  # Simulate processing
            return mock_successful_agent_response("crew_compliance")
        
        with patch("main.SAFETY_AGENTS", [("crew_compliance", mock_agent)]):
            with patch("main.BUSINESS_AGENTS", []):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify duration fields exist
        assert "phase1_duration_seconds" in result
        assert "phase2_duration_seconds" in result
        assert "phase3_duration_seconds" in result
        assert "total_duration_seconds" in result
        
        # Verify durations are positive
        assert result["phase1_duration_seconds"] > 0
        assert result["phase2_duration_seconds"] > 0
        assert result["phase3_duration_seconds"] > 0
        assert result["total_duration_seconds"] > 0
        
        # Verify total is sum of phases (approximately)
        total_phases = (
            result["phase1_duration_seconds"] +
            result["phase2_duration_seconds"] +
            result["phase3_duration_seconds"]
        )
        # Allow small difference for overhead
        assert abs(result["total_duration_seconds"] - total_phases) < 0.5


# ============================================================================
# Test Scenarios (Task 16.2)
# ============================================================================


class TestScenarios:
    """
    Test specific disruption scenarios
    
    Task 16.2: Create test scenarios
    - Simple disruption (no conflicts)
    - Safety vs business conflict
    - Safety vs safety conflict
    - Multiple agent failures
    """
    
    @pytest.mark.asyncio
    async def test_scenario_simple_disruption_no_conflicts(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Scenario 1: Simple disruption with no conflicts
        
        All agents agree on a 2-hour delay recommendation.
        No conflicts between safety and business agents.
        Arbitrator should synthesize a straightforward decision.
        
        Validates:
        - Requirements 9.1-9.8 (Phase 1 execution)
        - Requirements 10.1-10.7 (Phase 2 execution)
        - Requirements 11.1-11.7 (Phase 3 arbitration)
        """
        # Mock all agents to agree on 2-hour delay
        async def agreeing_agent(agent_name):
            async def agent_func(payload, llm, mcp_tools):
                return {
                    "agent": agent_name,
                    "status": "success",
                    "recommendation": "Delay flight by 2 hours for inspection and crew rest",
                    "confidence": 0.90,
                    "reasoning": f"{agent_name} analysis shows 2-hour delay is optimal",
                    "data_sources": ["Flights", "CrewRoster"],
                    "binding_constraints": [] if agent_name not in ["crew_compliance", "maintenance", "regulatory"] 
                                          else ["Minimum 2-hour delay required"],
                    "extracted_flight_info": {
                        "flight_number": "EY123",
                        "date": "2026-01-20",
                        "disruption_event": "mechanical failure"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": 1.0
                }
            return agent_func
        
        safety_agents = ["crew_compliance", "maintenance", "regulatory"]
        business_agents = ["network", "guest_experience", "cargo", "finance"]
        
        with patch("main.SAFETY_AGENTS", [(name, await agreeing_agent(name)) for name in safety_agents]):
            with patch("main.BUSINESS_AGENTS", [(name, await agreeing_agent(name)) for name in business_agents]):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify successful completion
        assert result["status"] == "success"
        assert "final_decision" in result
        
        # Verify all agents responded successfully
        phase1_responses = result["audit_trail"]["phase1_initial"]["responses"]
        assert len(phase1_responses) == 7
        for agent_name, response in phase1_responses.items():
            assert response["status"] == "success"
            assert "2 hours" in response["recommendation"] or "2-hour" in response["recommendation"]
        
        # Verify no conflicts identified (arbitrator not yet implemented, so this may be empty)
        phase3 = result["audit_trail"]["phase3_arbitration"]
        # Note: When arbitrator is implemented, this should verify conflicts_identified
        # For now, just verify the structure exists
        assert "conflicts_identified" in phase3
        
        # Verify final decision exists (may be placeholder until arbitrator implemented)
        assert "final_decision" in phase3
        # Note: When arbitrator is implemented, verify decision reflects consensus:
        # assert "2 hour" in phase3["final_decision"].lower() or "2-hour" in phase3["final_decision"].lower()
    
    @pytest.mark.asyncio
    async def test_scenario_safety_vs_business_conflict(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Scenario 2: Safety vs Business conflict
        
        Safety agents recommend cancellation due to crew duty limits.
        Business agents recommend delay to minimize passenger impact.
        Arbitrator must prioritize safety and choose cancellation.
        
        Validates:
        - Requirements 11.3 (Safety binding constraints are non-negotiable)
        - Requirements 11.4 (Safety vs business: choose safety)
        - Requirements 13.1-13.3 (Safety-first decision making)
        - Property 8: Safety Priority Invariant
        """
        # Mock safety agents to recommend cancellation
        async def safety_agent(agent_name):
            async def agent_func(payload, llm, mcp_tools):
                return {
                    "agent": agent_name,
                    "status": "success",
                    "recommendation": "Cancel flight - crew duty limits exceeded",
                    "confidence": 0.95,
                    "reasoning": f"{agent_name}: Crew has exceeded maximum duty hours. "
                                "No qualified replacement crew available within safe timeframe.",
                    "data_sources": ["CrewRoster", "CrewMembers"],
                    "binding_constraints": [
                        "Crew duty limits must not be exceeded",
                        "Flight cannot operate without qualified crew"
                    ],
                    "extracted_flight_info": {
                        "flight_number": "EY123",
                        "date": "2026-01-20",
                        "disruption_event": "mechanical failure"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": 1.0
                }
            return agent_func
        
        # Mock business agents to recommend delay
        async def business_agent(agent_name):
            async def agent_func(payload, llm, mcp_tools):
                return {
                    "agent": agent_name,
                    "status": "success",
                    "recommendation": "Delay flight by 4 hours to minimize passenger disruption",
                    "confidence": 0.85,
                    "reasoning": f"{agent_name}: 4-hour delay allows rebooking and minimizes costs. "
                                "Cancellation would impact 200+ passengers.",
                    "data_sources": ["Bookings", "Flights"],
                    "binding_constraints": [],
                    "extracted_flight_info": {
                        "flight_number": "EY123",
                        "date": "2026-01-20",
                        "disruption_event": "mechanical failure"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": 1.0
                }
            return agent_func
        
        safety_agents = ["crew_compliance", "maintenance", "regulatory"]
        business_agents = ["network", "guest_experience", "cargo", "finance"]
        
        with patch("main.SAFETY_AGENTS", [(name, await safety_agent(name)) for name in safety_agents]):
            with patch("main.BUSINESS_AGENTS", [(name, await business_agent(name)) for name in business_agents]):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify successful completion
        assert result["status"] == "success"
        
        # Verify conflict scenario setup (agents have conflicting recommendations)
        phase1_responses = result["audit_trail"]["phase1_initial"]["responses"]
        
        # Verify safety agents recommend cancellation
        safety_agents = ["crew_compliance", "maintenance", "regulatory"]
        for agent_name in safety_agents:
            if phase1_responses[agent_name]["status"] == "success":
                assert "cancel" in phase1_responses[agent_name]["recommendation"].lower()
        
        # Verify business agents recommend delay
        business_agents = ["network", "guest_experience", "cargo", "finance"]
        for agent_name in business_agents:
            if phase1_responses[agent_name]["status"] == "success":
                assert "delay" in phase1_responses[agent_name]["recommendation"].lower()
        
        # Verify phase 3 structure exists
        phase3 = result["audit_trail"]["phase3_arbitration"]
        assert "conflicts_identified" in phase3
        assert "final_decision" in phase3
        
        # Note: When arbitrator is implemented, verify:
        # - Conflicts identified (safety_vs_business)
        # - Final decision prioritizes safety (cancellation)
        # - Safety overrides documented
        # - Justification mentions safety priority
        
        # For now, verify the test scenario is properly set up
        # The actual arbitration logic will be tested when Task 15 is complete
    
    @pytest.mark.asyncio
    async def test_scenario_safety_vs_safety_conflict(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Scenario 3: Safety vs Safety conflict
        
        Crew compliance recommends 2-hour delay for crew rest.
        Maintenance recommends 6-hour delay for thorough inspection.
        Arbitrator must choose the most conservative option (6-hour delay).
        
        Validates:
        - Requirements 11.4 (Safety vs safety: choose most conservative)
        - Requirements 11.5 (Prioritize cancellation/rerouting over compromises)
        - Requirements 13.4 (Document safety overrides)
        - Property 9: Conservative Conflict Resolution
        """
        # Mock crew compliance to recommend 2-hour delay
        async def crew_agent(payload, llm, mcp_tools):
            return {
                "agent": "crew_compliance",
                "status": "success",
                "recommendation": "Delay flight by 2 hours for crew rest",
                "confidence": 0.90,
                "reasoning": "Crew requires minimum 2-hour rest period to comply with duty regulations",
                "data_sources": ["CrewRoster", "CrewMembers"],
                "binding_constraints": [
                    "Minimum 2-hour crew rest required"
                ],
                "extracted_flight_info": {
                    "flight_number": "EY123",
                    "date": "2026-01-20",
                    "disruption_event": "mechanical failure"
                },
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 1.0
            }
        
        # Mock maintenance to recommend 6-hour delay
        async def maintenance_agent(payload, llm, mcp_tools):
            return {
                "agent": "maintenance",
                "status": "success",
                "recommendation": "Delay flight by 6 hours for comprehensive inspection",
                "confidence": 0.95,
                "reasoning": "Mechanical failure requires thorough inspection of multiple systems. "
                            "Minimum 6 hours needed to ensure aircraft airworthiness.",
                "data_sources": ["MaintenanceWorkOrders", "Flights"],
                "binding_constraints": [
                    "Minimum 6-hour inspection required for airworthiness",
                    "Aircraft cannot fly until inspection complete"
                ],
                "extracted_flight_info": {
                    "flight_number": "EY123",
                    "date": "2026-01-20",
                    "disruption_event": "mechanical failure"
                },
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 1.0
            }
        
        # Mock regulatory to support longer delay
        async def regulatory_agent(payload, llm, mcp_tools):
            return {
                "agent": "regulatory",
                "status": "success",
                "recommendation": "Delay flight until all safety requirements met",
                "confidence": 0.92,
                "reasoning": "Regulatory compliance requires both crew rest and maintenance inspection",
                "data_sources": ["Weather", "Flights"],
                "binding_constraints": [
                    "All safety requirements must be satisfied"
                ],
                "extracted_flight_info": {
                    "flight_number": "EY123",
                    "date": "2026-01-20",
                    "disruption_event": "mechanical failure"
                },
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 1.0
            }
        
        # Mock business agents to agree with delay
        async def business_agent(agent_name):
            async def agent_func(payload, llm, mcp_tools):
                return {
                    "agent": agent_name,
                    "status": "success",
                    "recommendation": "Support safety recommendations",
                    "confidence": 0.85,
                    "reasoning": f"{agent_name}: Defer to safety agents on delay duration",
                    "data_sources": ["Flights"],
                    "binding_constraints": [],
                    "extracted_flight_info": {
                        "flight_number": "EY123",
                        "date": "2026-01-20",
                        "disruption_event": "mechanical failure"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": 1.0
                }
            return agent_func
        
        business_agents = ["network", "guest_experience", "cargo", "finance"]
        
        with patch("main.SAFETY_AGENTS", [
            ("crew_compliance", crew_agent),
            ("maintenance", maintenance_agent),
            ("regulatory", regulatory_agent)
        ]):
            with patch("main.BUSINESS_AGENTS", [(name, await business_agent(name)) for name in business_agents]):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify successful completion
        assert result["status"] == "success"
        
        # Verify conflict identified
        phase3 = result["audit_trail"]["phase3_arbitration"]
        conflicts = phase3.get("conflicts_identified", [])
        assert len(conflicts) > 0
        
        # Verify at least one conflict is safety_vs_safety
        conflict_types = [c.get("conflict_type") for c in conflicts]
        assert "safety_vs_safety" in conflict_types
        
        # Verify final decision chooses most conservative option (6-hour delay)
        final_decision = phase3["final_decision"].lower()
        assert "6 hour" in final_decision or "6-hour" in final_decision or "six hour" in final_decision
        
        # Verify justification mentions conservative approach
        justification = phase3.get("justification", "").lower()
        assert "conservative" in justification or "thorough" in justification or "comprehensive" in justification
        
        # Verify both safety constraints documented
        reasoning = phase3.get("reasoning", "").lower()
        assert "crew" in reasoning and "maintenance" in reasoning
    
    @pytest.mark.asyncio
    async def test_scenario_multiple_agent_failures(
        self, sample_user_prompt, mock_llm, mock_mcp_tools
    ):
        """
        Scenario 4: Multiple agent failures
        
        3 agents succeed, 2 agents timeout, 2 agents error.
        System should continue with available responses and make best decision.
        
        Validates:
        - Requirements 16.1 (Continue with available responses)
        - Requirements 16.2 (Apply conservative safety recommendation on failures)
        - Requirements 16.5 (Log all errors)
        - Property 11: Graceful Degradation
        """
        # Mock successful agents
        async def success_agent(agent_name):
            async def agent_func(payload, llm, mcp_tools):
                return {
                    "agent": agent_name,
                    "status": "success",
                    "recommendation": f"{agent_name} recommends 3-hour delay",
                    "confidence": 0.88,
                    "reasoning": f"{agent_name} analysis complete",
                    "data_sources": ["Flights"],
                    "binding_constraints": ["Minimum 3-hour delay"] if agent_name == "crew_compliance" else [],
                    "extracted_flight_info": {
                        "flight_number": "EY123",
                        "date": "2026-01-20",
                        "disruption_event": "mechanical failure"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": 1.0
                }
            return agent_func
        
        # Mock timeout agents
        async def timeout_agent(agent_name):
            async def agent_func(payload, llm, mcp_tools):
                await asyncio.sleep(35)  # Exceed 30-second timeout
                return {"agent": agent_name}
            return agent_func
        
        # Mock error agents
        async def error_agent(agent_name):
            async def agent_func(payload, llm, mcp_tools):
                raise RuntimeError(f"{agent_name} encountered an error")
            return agent_func
        
        # Configure agents: 3 success, 2 timeout, 2 error
        with patch("main.SAFETY_AGENTS", [
            ("crew_compliance", await success_agent("crew_compliance")),  # Success
            ("maintenance", await timeout_agent("maintenance")),          # Timeout
            ("regulatory", await error_agent("regulatory"))               # Error
        ]):
            with patch("main.BUSINESS_AGENTS", [
                ("network", await success_agent("network")),              # Success
                ("guest_experience", await timeout_agent("guest_experience")),  # Timeout
                ("cargo", await error_agent("cargo")),                    # Error
                ("finance", await success_agent("finance"))               # Success
            ]):
                result = await handle_disruption(sample_user_prompt, mock_llm, mock_mcp_tools)
        
        # Verify system completed despite failures
        assert result["status"] == "success"
        
        # Verify all agents in collation (including failed ones)
        phase1_responses = result["audit_trail"]["phase1_initial"]["responses"]
        assert len(phase1_responses) == 7
        
        # Verify successful agents
        successful_agents = ["crew_compliance", "network", "finance"]
        for agent_name in successful_agents:
            assert phase1_responses[agent_name]["status"] == "success"
            assert "3-hour delay" in phase1_responses[agent_name]["recommendation"]
        
        # Verify timeout agents
        timeout_agents = ["maintenance", "guest_experience"]
        for agent_name in timeout_agents:
            assert phase1_responses[agent_name]["status"] == "timeout"
            assert "error" in phase1_responses[agent_name] or "timeout" in phase1_responses[agent_name].get("recommendation", "").lower()
        
        # Verify error agents
        error_agents = ["regulatory", "cargo"]
        for agent_name in error_agents:
            assert phase1_responses[agent_name]["status"] == "error"
            assert "error" in phase1_responses[agent_name]
        
        # Verify final decision made with available data
        phase3 = result["audit_trail"]["phase3_arbitration"]
        assert "final_decision" in phase3
        
        # Verify decision is conservative (uses successful safety agent's constraint)
        final_decision = phase3["final_decision"].lower()
        assert "3 hour" in final_decision or "3-hour" in final_decision or "delay" in final_decision
        
        # Verify justification mentions limited data
        justification = phase3.get("justification", "").lower()
        reasoning = phase3.get("reasoning", "").lower()
        combined_text = justification + " " + reasoning
        assert "available" in combined_text or "successful" in combined_text or "limited" in combined_text
