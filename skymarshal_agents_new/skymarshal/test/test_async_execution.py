"""
Unit tests for async execution patterns and error handling.

Tests verify:
- Agent-specific timeouts (safety: 60s, business: 45s)
- Safety agent failure halt logic
- Business agent failure continuation
- Phase synchronization
- Partial failure handling
- Enhanced error logging

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Import from main module
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import (
    run_agent_safely,
    phase1_initial_recommendations,
    phase2_revision_round,
    AGENT_TIMEOUTS,
    SAFETY_AGENT_NAMES,
    SAFETY_AGENTS,
    BUSINESS_AGENTS,
)


class TestAgentTimeouts:
    """Test agent-specific timeout configuration"""
    
    def test_safety_agent_timeouts_are_60_seconds(self):
        """Verify safety agents have 60s timeout"""
        assert AGENT_TIMEOUTS["crew_compliance"] == 60
        assert AGENT_TIMEOUTS["maintenance"] == 60
        assert AGENT_TIMEOUTS["regulatory"] == 60
    
    def test_business_agent_timeouts_are_45_seconds(self):
        """Verify business agents have 45s timeout"""
        assert AGENT_TIMEOUTS["network"] == 45
        assert AGENT_TIMEOUTS["guest_experience"] == 45
        assert AGENT_TIMEOUTS["cargo"] == 45
        assert AGENT_TIMEOUTS["finance"] == 45
    
    def test_all_agents_have_timeout_configured(self):
        """Verify all agents have timeout configuration"""
        all_agent_names = [name for name, _ in SAFETY_AGENTS + BUSINESS_AGENTS]
        for agent_name in all_agent_names:
            assert agent_name in AGENT_TIMEOUTS, f"{agent_name} missing timeout config"


class TestRunAgentSafely:
    """Test run_agent_safely wrapper function"""
    
    @pytest.mark.asyncio
    async def test_successful_agent_execution(self):
        """Test successful agent execution returns correct result"""
        # Mock agent function
        async def mock_agent(payload, llm, mcp_tools):
            return {
                "recommendation": "Test recommendation",
                "confidence": 0.95,
                "reasoning": "Test reasoning"
            }
        
        result = await run_agent_safely(
            agent_name="test_agent",
            agent_fn=mock_agent,
            payload={"user_prompt": "test"},
            llm=MagicMock(),
            mcp_tools=[],
            timeout=60
        )
        
        assert result["status"] == "success"
        assert result["agent"] == "test_agent"
        assert result["recommendation"] == "Test recommendation"
        assert result["confidence"] == 0.95
        assert "duration_seconds" in result
        assert result["duration_seconds"] >= 0
    
    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self):
        """Test agent timeout is caught and handled gracefully"""
        # Mock agent that takes too long
        async def slow_agent(payload, llm, mcp_tools):
            await asyncio.sleep(10)  # Sleep longer than timeout
            return {"recommendation": "Should not reach here"}
        
        result = await run_agent_safely(
            agent_name="slow_agent",
            agent_fn=slow_agent,
            payload={"user_prompt": "test"},
            llm=MagicMock(),
            mcp_tools=[],
            timeout=0.1  # Very short timeout for testing
        )
        
        assert result["status"] == "timeout"
        assert result["agent"] == "slow_agent"
        assert "timeout" in result["error"].lower()
        assert "duration_seconds" in result
        assert result["timeout_threshold"] == 0.1
    
    @pytest.mark.asyncio
    async def test_safety_agent_timeout_marked_critical(self):
        """Test safety agent timeout is marked as critical"""
        # Mock safety agent that times out
        async def slow_safety_agent(payload, llm, mcp_tools):
            await asyncio.sleep(10)
            return {}
        
        result = await run_agent_safely(
            agent_name="crew_compliance",  # Safety agent
            agent_fn=slow_safety_agent,
            payload={"user_prompt": "test"},
            llm=MagicMock(),
            mcp_tools=[],
            timeout=0.1
        )
        
        assert result["status"] == "timeout"
        assert result["is_safety_critical"] is True
    
    @pytest.mark.asyncio
    async def test_business_agent_timeout_not_marked_critical(self):
        """Test business agent timeout is not marked as critical"""
        # Mock business agent that times out
        async def slow_business_agent(payload, llm, mcp_tools):
            await asyncio.sleep(10)
            return {}
        
        result = await run_agent_safely(
            agent_name="network",  # Business agent
            agent_fn=slow_business_agent,
            payload={"user_prompt": "test"},
            llm=MagicMock(),
            mcp_tools=[],
            timeout=0.1
        )
        
        assert result["status"] == "timeout"
        assert result["is_safety_critical"] is False
    
    @pytest.mark.asyncio
    async def test_agent_exception_handling(self):
        """Test agent exceptions are caught and handled gracefully"""
        # Mock agent that raises exception
        async def failing_agent(payload, llm, mcp_tools):
            raise ValueError("Test error")
        
        result = await run_agent_safely(
            agent_name="failing_agent",
            agent_fn=failing_agent,
            payload={"user_prompt": "test"},
            llm=MagicMock(),
            mcp_tools=[],
            timeout=60
        )
        
        assert result["status"] == "error"
        assert result["agent"] == "failing_agent"
        assert result["error"] == "Test error"
        assert result["error_type"] == "ValueError"
        assert "duration_seconds" in result
    
    @pytest.mark.asyncio
    async def test_safety_agent_exception_marked_critical(self):
        """Test safety agent exception is marked as critical"""
        # Mock safety agent that raises exception
        async def failing_safety_agent(payload, llm, mcp_tools):
            raise RuntimeError("Safety check failed")
        
        result = await run_agent_safely(
            agent_name="maintenance",  # Safety agent
            agent_fn=failing_safety_agent,
            payload={"user_prompt": "test"},
            llm=MagicMock(),
            mcp_tools=[],
            timeout=60
        )
        
        assert result["status"] == "error"
        assert result["is_safety_critical"] is True
        assert result["error_type"] == "RuntimeError"


class TestSafetyAgentFailureHalt:
    """Test safety agent failure halt logic"""
    
    @pytest.mark.asyncio
    async def test_phase1_halts_on_safety_agent_failure(self):
        """Test Phase 1 halts execution when safety agent fails"""
        # Mock LLM and MCP tools
        mock_llm = MagicMock()
        mock_mcp_tools = []
        
        # Patch the agent functions
        with patch('main.analyze_crew_compliance') as mock_crew, \
             patch('main.analyze_maintenance') as mock_maint, \
             patch('main.analyze_regulatory') as mock_reg, \
             patch('main.analyze_network') as mock_net, \
             patch('main.analyze_guest_experience') as mock_guest, \
             patch('main.analyze_cargo') as mock_cargo, \
             patch('main.analyze_finance') as mock_fin:
            
            # Make crew_compliance fail
            async def failing_crew(*args, **kwargs):
                raise RuntimeError("Crew compliance check failed")
            
            mock_crew.side_effect = failing_crew
            
            # Make other agents succeed
            async def success_agent(*args, **kwargs):
                return {
                    "recommendation": "OK",
                    "confidence": 0.9,
                    "reasoning": "Test"
                }
            
            mock_maint.side_effect = success_agent
            mock_reg.side_effect = success_agent
            mock_net.side_effect = success_agent
            mock_guest.side_effect = success_agent
            mock_cargo.side_effect = success_agent
            mock_fin.side_effect = success_agent
            
            # Execute Phase 1 and expect RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                await phase1_initial_recommendations(
                    user_prompt="Test disruption",
                    llm=mock_llm,
                    mcp_tools=mock_mcp_tools
                )
            
            # Verify error message mentions safety agent failure
            assert "Safety-critical agent(s) failed" in str(exc_info.value)
            assert "crew_compliance" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_phase1_continues_on_business_agent_failure(self):
        """Test Phase 1 continues when only business agent fails"""
        # Mock LLM and MCP tools
        mock_llm = MagicMock()
        mock_mcp_tools = []
        
        # Patch the agent functions
        with patch('main.analyze_crew_compliance') as mock_crew, \
             patch('main.analyze_maintenance') as mock_maint, \
             patch('main.analyze_regulatory') as mock_reg, \
             patch('main.analyze_network') as mock_net, \
             patch('main.analyze_guest_experience') as mock_guest, \
             patch('main.analyze_cargo') as mock_cargo, \
             patch('main.analyze_finance') as mock_fin:
            
            # Make network (business agent) fail
            async def failing_network(*args, **kwargs):
                raise RuntimeError("Network analysis failed")
            
            mock_net.side_effect = failing_network
            
            # Make all other agents succeed
            async def success_agent(*args, **kwargs):
                return {
                    "recommendation": "OK",
                    "confidence": 0.9,
                    "reasoning": "Test",
                    "binding_constraints": [],
                    "data_sources": []
                }
            
            mock_crew.side_effect = success_agent
            mock_maint.side_effect = success_agent
            mock_reg.side_effect = success_agent
            mock_guest.side_effect = success_agent
            mock_cargo.side_effect = success_agent
            mock_fin.side_effect = success_agent
            
            # Execute Phase 1 - should NOT raise exception
            result = await phase1_initial_recommendations(
                user_prompt="Test disruption",
                llm=mock_llm,
                mcp_tools=mock_mcp_tools
            )
            
            # Verify result is a Collation object
            assert result.phase == "initial"
            assert "network" in result.responses
            assert result.responses["network"].status == "error"
            
            # Verify other agents succeeded
            assert result.responses["crew_compliance"].status == "success"
            assert result.responses["maintenance"].status == "success"


class TestPhaseSynchronization:
    """Test phase synchronization and ordering"""
    
    @pytest.mark.asyncio
    async def test_phase1_completes_before_phase2(self):
        """Test Phase 1 fully completes before Phase 2 starts"""
        # This is implicitly tested by the orchestrator flow
        # We verify by checking that Phase 2 receives Phase 1 results
        
        # Mock successful agents
        async def mock_agent(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate work
            return {
                "recommendation": "OK",
                "confidence": 0.9,
                "reasoning": "Test",
                "binding_constraints": [],
                "data_sources": []
            }
        
        mock_llm = MagicMock()
        mock_mcp_tools = []
        
        with patch('main.analyze_crew_compliance', side_effect=mock_agent), \
             patch('main.analyze_maintenance', side_effect=mock_agent), \
             patch('main.analyze_regulatory', side_effect=mock_agent), \
             patch('main.analyze_network', side_effect=mock_agent), \
             patch('main.analyze_guest_experience', side_effect=mock_agent), \
             patch('main.analyze_cargo', side_effect=mock_agent), \
             patch('main.analyze_finance', side_effect=mock_agent):
            
            # Execute Phase 1
            phase1_result = await phase1_initial_recommendations(
                user_prompt="Test disruption",
                llm=mock_llm,
                mcp_tools=mock_mcp_tools
            )
            
            # Verify Phase 1 completed
            assert phase1_result.phase == "initial"
            assert len(phase1_result.responses) == 7
            
            # Execute Phase 2 with Phase 1 results
            phase2_result = await phase2_revision_round(
                user_prompt="Test disruption",
                initial_collation=phase1_result,
                llm=mock_llm,
                mcp_tools=mock_mcp_tools
            )
            
            # Verify Phase 2 completed
            assert phase2_result.phase == "revision"
            assert len(phase2_result.responses) == 7


class TestPartialFailureHandling:
    """Test handling of partial agent failures"""
    
    @pytest.mark.asyncio
    async def test_multiple_business_agent_failures_continue(self):
        """Test execution continues with multiple business agent failures"""
        mock_llm = MagicMock()
        mock_mcp_tools = []
        
        with patch('main.analyze_crew_compliance') as mock_crew, \
             patch('main.analyze_maintenance') as mock_maint, \
             patch('main.analyze_regulatory') as mock_reg, \
             patch('main.analyze_network') as mock_net, \
             patch('main.analyze_guest_experience') as mock_guest, \
             patch('main.analyze_cargo') as mock_cargo, \
             patch('main.analyze_finance') as mock_fin:
            
            # Make 3 business agents fail
            async def failing_agent(*args, **kwargs):
                raise RuntimeError("Agent failed")
            
            mock_net.side_effect = failing_agent
            mock_cargo.side_effect = failing_agent
            mock_fin.side_effect = failing_agent
            
            # Make safety agents and remaining business agents succeed
            async def success_agent(*args, **kwargs):
                return {
                    "recommendation": "OK",
                    "confidence": 0.9,
                    "reasoning": "Test",
                    "binding_constraints": [],
                    "data_sources": []
                }
            
            mock_crew.side_effect = success_agent
            mock_maint.side_effect = success_agent
            mock_reg.side_effect = success_agent
            mock_guest.side_effect = success_agent
            
            # Execute Phase 1 - should NOT raise exception
            result = await phase1_initial_recommendations(
                user_prompt="Test disruption",
                llm=mock_llm,
                mcp_tools=mock_mcp_tools
            )
            
            # Verify execution continued
            assert result.phase == "initial"
            
            # Verify failed agents have error status
            assert result.responses["network"].status == "error"
            assert result.responses["cargo"].status == "error"
            assert result.responses["finance"].status == "error"
            
            # Verify successful agents have success status
            assert result.responses["crew_compliance"].status == "success"
            assert result.responses["maintenance"].status == "success"
            assert result.responses["regulatory"].status == "success"
            assert result.responses["guest_experience"].status == "success"
            
            # Verify counts
            counts = result.get_agent_count()
            assert counts["success"] == 4
            assert counts["error"] == 3


class TestErrorLogging:
    """Test enhanced error logging"""
    
    @pytest.mark.asyncio
    async def test_timeout_includes_threshold(self):
        """Test timeout error includes timeout threshold"""
        async def slow_agent(*args, **kwargs):
            await asyncio.sleep(10)
            return {}
        
        result = await run_agent_safely(
            agent_name="test_agent",
            agent_fn=slow_agent,
            payload={"user_prompt": "test"},
            llm=MagicMock(),
            mcp_tools=[],
            timeout=0.1
        )
        
        assert result["status"] == "timeout"
        assert result["timeout_threshold"] == 0.1
        assert "duration_seconds" in result
    
    @pytest.mark.asyncio
    async def test_error_includes_type(self):
        """Test error includes exception type"""
        async def failing_agent(*args, **kwargs):
            raise ValueError("Test error")
        
        result = await run_agent_safely(
            agent_name="test_agent",
            agent_fn=failing_agent,
            payload={"user_prompt": "test"},
            llm=MagicMock(),
            mcp_tools=[],
            timeout=60
        )
        
        assert result["status"] == "error"
        assert result["error_type"] == "ValueError"
        assert result["error"] == "Test error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
