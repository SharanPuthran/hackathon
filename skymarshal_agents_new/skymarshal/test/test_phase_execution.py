"""Tests for phase execution methods in orchestrator"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import (
    phase1_initial_recommendations,
    phase2_revision_round,
    phase3_arbitration,
    handle_disruption,
)
from agents.schemas import AgentResponse, Collation


@pytest.mark.asyncio
async def test_phase1_initial_recommendations():
    """Test phase 1 returns collation with all agents"""
    user_prompt = "Flight EY123 on Jan 20th had a mechanical failure"
    
    # Mock LLM and MCP tools
    mock_llm = Mock()
    mock_mcp_tools = []
    
    # Mock agent functions to return success
    mock_response = {
        "agent": "test_agent1",
        "recommendation": "Test rec 1",
        "confidence": 0.95,
        "reasoning": "Test reasoning",
        "data_sources": ["test_source"],
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "duration_seconds": 1.0
    }
    
    with patch("main.SAFETY_AGENTS", [("test_agent1", AsyncMock(return_value=mock_response))]):
        with patch("main.BUSINESS_AGENTS", [("test_agent2", AsyncMock(return_value={**mock_response, "agent": "test_agent2"}))]):
            result = await phase1_initial_recommendations(user_prompt, mock_llm, mock_mcp_tools)
    
    # Verify structure - should be Collation model
    assert isinstance(result, Collation)
    assert result.phase == "initial"
    assert "test_agent1" in result.responses
    assert "test_agent2" in result.responses
    assert isinstance(result.responses["test_agent1"], AgentResponse)
    assert result.duration_seconds > 0
    
    # Test helper methods
    successful = result.get_successful_responses()
    assert len(successful) == 2
    counts = result.get_agent_count()
    assert counts["success"] == 2


@pytest.mark.asyncio
async def test_phase2_revision_round():
    """Test phase 2 returns collation with revised recommendations"""
    user_prompt = "Flight EY123 on Jan 20th had a mechanical failure"
    
    # Create initial collation using Pydantic model
    initial_collation = Collation(
        phase="initial",
        responses={
            "test_agent1": AgentResponse(
                agent_name="test_agent1",
                recommendation="Initial rec 1",
                confidence=0.9,
                reasoning="Initial reasoning",
                data_sources=["test"],
                timestamp=datetime.now().isoformat()
            )
        },
        timestamp=datetime.now().isoformat(),
        duration_seconds=1.0
    )
    
    # Mock LLM and MCP tools
    mock_llm = Mock()
    mock_mcp_tools = []
    
    # Mock agent functions to return success
    mock_response = {
        "agent": "test_agent1",
        "recommendation": "Revised rec 1",
        "confidence": 0.95,
        "reasoning": "Revised reasoning",
        "data_sources": ["test_source"],
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "duration_seconds": 1.0
    }
    
    with patch("main.SAFETY_AGENTS", [("test_agent1", AsyncMock(return_value=mock_response))]):
        with patch("main.BUSINESS_AGENTS", [("test_agent2", AsyncMock(return_value={**mock_response, "agent": "test_agent2"}))]):
            result = await phase2_revision_round(user_prompt, initial_collation, mock_llm, mock_mcp_tools)
    
    # Verify structure - should be Collation model
    assert isinstance(result, Collation)
    assert result.phase == "revision"
    assert "test_agent1" in result.responses
    assert "test_agent2" in result.responses
    assert isinstance(result.responses["test_agent1"], AgentResponse)
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_phase3_arbitration():
    """Test phase 3 returns arbitration decision (placeholder)"""
    # Create revised collation using Pydantic model
    revised_collation = Collation(
        phase="revision",
        responses={
            "test_agent1": AgentResponse(
                agent_name="test_agent1",
                recommendation="Revised rec 1",
                confidence=0.95,
                reasoning="Revised reasoning 1",
                data_sources=["test"],
                timestamp=datetime.now().isoformat(),
                status="success"
            ),
            "test_agent2": AgentResponse(
                agent_name="test_agent2",
                recommendation="Revised rec 2",
                confidence=0.90,
                reasoning="Revised reasoning 2",
                data_sources=["test"],
                timestamp=datetime.now().isoformat(),
                status="success"
            )
        },
        timestamp=datetime.now().isoformat(),
        duration_seconds=1.0
    )
    
    # Mock LLM
    mock_llm = Mock()
    
    result = await phase3_arbitration(revised_collation, mock_llm)
    
    # Verify structure (placeholder implementation)
    assert result["phase"] == "arbitration"
    assert "final_decision" in result
    assert "recommendations" in result
    assert "conflicts_identified" in result
    assert "conflict_resolutions" in result
    assert "safety_overrides" in result
    assert "justification" in result
    assert "reasoning" in result
    assert "confidence" in result
    assert "timestamp" in result
    assert "duration_seconds" in result
    
    # Verify placeholder content
    assert len(result["recommendations"]) == 2
    assert "test_agent1" in result["recommendations"][0]
    assert "test_agent2" in result["recommendations"][1]


@pytest.mark.asyncio
async def test_handle_disruption_three_phase_flow():
    """Test handle_disruption executes all three phases"""
    user_prompt = "Flight EY123 on Jan 20th had a mechanical failure"
    
    # Mock LLM and MCP tools
    mock_llm = Mock()
    mock_mcp_tools = []
    
    # Mock all agent functions
    mock_agent_response = {
        "agent": "test_agent",
        "status": "success",
        "recommendation": "Test recommendation",
        "confidence": 0.95,
        "reasoning": "Test reasoning",
        "data_sources": ["test"],
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": 1.0
    }
    
    with patch("main.SAFETY_AGENTS", [("test_safety", AsyncMock(return_value=mock_agent_response))]):
        with patch("main.BUSINESS_AGENTS", [("test_business", AsyncMock(return_value=mock_agent_response))]):
            result = await handle_disruption(user_prompt, mock_llm, mock_mcp_tools)
    
    # Verify response structure
    assert result["status"] == "success"
    assert "final_decision" in result
    assert "audit_trail" in result
    assert "timestamp" in result
    
    # Verify audit trail contains all phases
    audit_trail = result["audit_trail"]
    assert audit_trail["user_prompt"] == user_prompt
    assert "phase1_initial" in audit_trail
    assert "phase2_revision" in audit_trail
    assert "phase3_arbitration" in audit_trail
    
    # Verify phase1 and phase2 are Collation dicts (from model_dump())
    assert audit_trail["phase1_initial"]["phase"] == "initial"
    assert "responses" in audit_trail["phase1_initial"]
    assert audit_trail["phase2_revision"]["phase"] == "revision"
    assert "responses" in audit_trail["phase2_revision"]
    
    # Verify phase durations
    assert "phase1_duration_seconds" in result
    assert "phase2_duration_seconds" in result
    assert "phase3_duration_seconds" in result
    assert "total_duration_seconds" in result


@pytest.mark.asyncio
async def test_handle_disruption_empty_prompt():
    """Test handle_disruption handles empty prompt"""
    user_prompt = ""
    
    # Mock LLM and MCP tools
    mock_llm = Mock()
    mock_mcp_tools = []
    
    result = await handle_disruption(user_prompt, mock_llm, mock_mcp_tools)
    
    # Verify validation failure
    assert result["status"] == "VALIDATION_FAILED"
    assert "reason" in result
    assert "No prompt provided" in result["reason"]


@pytest.mark.asyncio
async def test_phase_execution_order():
    """Test that phases execute in correct order"""
    user_prompt = "Flight EY123 on Jan 20th had a mechanical failure"
    
    # Track execution order
    execution_order = []
    
    async def mock_phase1(*args):
        execution_order.append("phase1")
        return Collation(
            phase="initial",
            responses={
                "test": AgentResponse(
                    agent_name="test",
                    recommendation="Test",
                    confidence=0.9,
                    reasoning="Test",
                    data_sources=[],
                    timestamp=datetime.now().isoformat(),
                    status="success"
                )
            },
            timestamp=datetime.now().isoformat(),
            duration_seconds=0.1
        )
    
    async def mock_phase2(*args):
        execution_order.append("phase2")
        return Collation(
            phase="revision",
            responses={
                "test": AgentResponse(
                    agent_name="test",
                    recommendation="Test",
                    confidence=0.9,
                    reasoning="Test",
                    data_sources=[],
                    timestamp=datetime.now().isoformat(),
                    status="success"
                )
            },
            timestamp=datetime.now().isoformat(),
            duration_seconds=0.1
        )
    
    async def mock_phase3(*args):
        execution_order.append("phase3")
        return {
            "phase": "arbitration",
            "final_decision": "Test decision",
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
    
    # Mock LLM and MCP tools
    mock_llm = Mock()
    mock_mcp_tools = []
    
    with patch("main.phase1_initial_recommendations", mock_phase1):
        with patch("main.phase2_revision_round", mock_phase2):
            with patch("main.phase3_arbitration", mock_phase3):
                result = await handle_disruption(user_prompt, mock_llm, mock_mcp_tools)
    
    # Verify execution order
    assert execution_order == ["phase1", "phase2", "phase3"]
    assert result["status"] == "success"



@pytest.mark.asyncio
async def test_collation_helper_methods():
    """Test Collation model helper methods"""
    # Create collation with mixed statuses
    collation = Collation(
        phase="initial",
        responses={
            "agent1": AgentResponse(
                agent_name="agent1",
                recommendation="Success rec",
                confidence=0.95,
                reasoning="Success reasoning",
                data_sources=["test"],
                timestamp=datetime.now().isoformat(),
                status="success"
            ),
            "agent2": AgentResponse(
                agent_name="agent2",
                recommendation="Timeout rec",
                confidence=0.0,
                reasoning="Timeout",
                data_sources=[],
                timestamp=datetime.now().isoformat(),
                status="timeout",
                error="Agent timeout"
            ),
            "agent3": AgentResponse(
                agent_name="agent3",
                recommendation="Error rec",
                confidence=0.0,
                reasoning="Error",
                data_sources=[],
                timestamp=datetime.now().isoformat(),
                status="error",
                error="Agent error"
            )
        },
        timestamp=datetime.now().isoformat(),
        duration_seconds=5.0
    )
    
    # Test get_successful_responses
    successful = collation.get_successful_responses()
    assert len(successful) == 1
    assert "agent1" in successful
    assert successful["agent1"].status == "success"
    
    # Test get_failed_responses
    failed = collation.get_failed_responses()
    assert len(failed) == 2
    assert "agent2" in failed
    assert "agent3" in failed
    
    # Test get_agent_count
    counts = collation.get_agent_count()
    assert counts["success"] == 1
    assert counts["timeout"] == 1
    assert counts["error"] == 1


@pytest.mark.asyncio
async def test_collation_with_error_responses():
    """Test collation handles agent errors gracefully"""
    user_prompt = "Flight EY123 on Jan 20th had a mechanical failure"
    
    # Mock LLM and MCP tools
    mock_llm = Mock()
    mock_mcp_tools = []
    
    # Mock agent that returns error
    async def mock_error_agent(*args):
        return {
            "agent": "error_agent",
            "status": "error",
            "error": "Test error",
            "duration_seconds": 1.0
        }
    
    # Mock agent that returns success
    async def mock_success_agent(*args):
        return {
            "agent": "success_agent",
            "status": "success",
            "recommendation": "Test recommendation",
            "confidence": 0.95,
            "reasoning": "Test reasoning",
            "data_sources": ["test"],
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": 1.0
        }
    
    with patch("main.SAFETY_AGENTS", [("error_agent", mock_error_agent)]):
        with patch("main.BUSINESS_AGENTS", [("success_agent", mock_success_agent)]):
            result = await phase1_initial_recommendations(user_prompt, mock_llm, mock_mcp_tools)
    
    # Verify collation contains both responses
    assert isinstance(result, Collation)
    assert "error_agent" in result.responses
    assert "success_agent" in result.responses
    
    # Verify error agent has error status
    assert result.responses["error_agent"].status == "error"
    assert result.responses["error_agent"].error is not None
    
    # Verify success agent has success status
    assert result.responses["success_agent"].status == "success"
    
    # Verify helper methods work correctly
    successful = result.get_successful_responses()
    assert len(successful) == 1
    assert "success_agent" in successful
    
    failed = result.get_failed_responses()
    assert len(failed) == 1
    assert "error_agent" in failed


@pytest.mark.asyncio
async def test_agent_timeout_handling():
    """Test that agents timeout after 30 seconds"""
    import asyncio
    from main import run_agent_safely
    
    # Mock LLM and MCP tools
    mock_llm = Mock()
    mock_mcp_tools = []
    
    # Mock agent that takes too long (simulates 35 seconds)
    async def slow_agent(*args):
        await asyncio.sleep(35)
        return {
            "agent": "slow_agent",
            "status": "success",
            "recommendation": "Should not reach here",
            "confidence": 0.95,
            "reasoning": "Should timeout",
            "data_sources": ["test"],
            "timestamp": datetime.now().isoformat()
        }
    
    # Create payload
    payload = {
        "user_prompt": "Test prompt",
        "phase": "initial"
    }
    
    # Run agent with default timeout (should be 30 seconds)
    result = await run_agent_safely(
        "slow_agent",
        slow_agent,
        payload,
        mock_llm,
        mock_mcp_tools
    )
    
    # Verify timeout occurred
    assert result["status"] == "timeout"
    assert result["agent"] == "slow_agent"
    assert "timeout" in result["error"].lower()
    assert "30" in result["error"]  # Should mention 30 second timeout
    assert result["duration_seconds"] >= 30  # Should have waited at least 30 seconds


@pytest.mark.asyncio
async def test_agent_completes_within_timeout():
    """Test that agents completing within 30 seconds succeed"""
    import asyncio
    from main import run_agent_safely
    
    # Mock LLM and MCP tools
    mock_llm = Mock()
    mock_mcp_tools = []
    
    # Mock agent that completes quickly
    async def fast_agent(*args):
        await asyncio.sleep(0.1)  # Simulate 100ms processing
        return {
            "agent": "fast_agent",
            "status": "success",
            "recommendation": "Quick recommendation",
            "confidence": 0.95,
            "reasoning": "Fast reasoning",
            "data_sources": ["test"],
            "timestamp": datetime.now().isoformat()
        }
    
    # Create payload
    payload = {
        "user_prompt": "Test prompt",
        "phase": "initial"
    }
    
    # Run agent with default timeout
    result = await run_agent_safely(
        "fast_agent",
        fast_agent,
        payload,
        mock_llm,
        mock_mcp_tools
    )
    
    # Verify success
    assert result["status"] == "success"
    assert result["agent"] == "fast_agent"
    assert result["recommendation"] == "Quick recommendation"
    assert result["duration_seconds"] < 30  # Should complete well before timeout
