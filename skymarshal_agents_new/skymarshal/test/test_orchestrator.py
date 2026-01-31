"""Unit tests for orchestrator functions in main.py"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path
from datetime import datetime
import asyncio
from hypothesis import given, strategies as st, settings

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import (
    augment_prompt_phase1,
    augment_prompt_phase2,
    run_agent_safely,
    AGENT_REGISTRY,
    SAFETY_AGENTS,
    BUSINESS_AGENTS,
)
from agents.schemas import AgentResponse


class TestPromptAugmentation:
    """Test prompt augmentation functions"""
    
    def test_augment_prompt_phase1_preserves_original(self):
        """Test that phase 1 augmentation preserves original prompt"""
        original = "Flight EY123 on Jan 20th had a mechanical failure"
        augmented = augment_prompt_phase1(original)
        
        # Verify original prompt is preserved
        assert original in augmented
        
        # Verify instruction is added
        assert "Please analyze this disruption" in augmented
        assert "initial recommendation" in augmented
        
        # Verify format (original + newlines + instruction)
        assert augmented.startswith(original)
        assert "\n\n" in augmented
    
    def test_augment_prompt_phase1_with_empty_prompt(self):
        """Test phase 1 augmentation with empty prompt"""
        original = ""
        augmented = augment_prompt_phase1(original)
        
        # Should still add instruction
        assert "Please analyze this disruption" in augmented
        assert "initial recommendation" in augmented
    
    def test_augment_prompt_phase1_with_special_characters(self):
        """Test phase 1 augmentation preserves special characters"""
        original = "Flight EY123 @ 14:30 UTC - mechanical failure (engine #2)"
        augmented = augment_prompt_phase1(original)
        
        # Verify all special characters preserved
        assert "@" in augmented
        assert "#" in augmented
        assert "(" in augmented
        assert ")" in augmented
        assert original in augmented
    
    def test_augment_prompt_phase2_preserves_original(self):
        """Test that phase 2 augmentation preserves original prompt"""
        original = "Flight EY123 on Jan 20th had a mechanical failure"
        collation = {
            "responses": {
                "crew_compliance": {
                    "recommendation": "Crew is available",
                    "confidence": 0.95
                }
            }
        }
        
        augmented = augment_prompt_phase2(original, collation)
        
        # Verify original prompt is preserved
        assert original in augmented
        
        # Verify instruction is added
        assert "Review other agents' recommendations" in augmented
        assert "revise if needed" in augmented
        
        # Verify other recommendations are included
        assert "CREW_COMPLIANCE" in augmented
        assert "Crew is available" in augmented
        assert "0.95" in augmented
    
    def test_augment_prompt_phase2_with_multiple_agents(self):
        """Test phase 2 augmentation with multiple agent responses"""
        original = "Flight EY123 on Jan 20th had a mechanical failure"
        collation = {
            "responses": {
                "crew_compliance": {
                    "recommendation": "Crew is available",
                    "confidence": 0.95
                },
                "maintenance": {
                    "recommendation": "Aircraft needs inspection",
                    "confidence": 0.90,
                    "binding_constraints": ["Must inspect engine before flight"]
                },
                "network": {
                    "recommendation": "Delay by 2 hours",
                    "confidence": 0.85
                }
            }
        }
        
        augmented = augment_prompt_phase2(original, collation)
        
        # Verify all agents included
        assert "CREW_COMPLIANCE" in augmented
        assert "MAINTENANCE" in augmented
        assert "NETWORK" in augmented
        
        # Verify all recommendations included
        assert "Crew is available" in augmented
        assert "Aircraft needs inspection" in augmented
        assert "Delay by 2 hours" in augmented
        
        # Verify binding constraints included
        assert "Binding Constraints" in augmented
        assert "Must inspect engine before flight" in augmented
    
    def test_augment_prompt_phase2_with_empty_collation(self):
        """Test phase 2 augmentation with empty collation"""
        original = "Flight EY123 on Jan 20th had a mechanical failure"
        collation = {"responses": {}}
        
        augmented = augment_prompt_phase2(original, collation)
        
        # Should still include original and instruction
        assert original in augmented
        assert "Review other agents' recommendations" in augmented
    
    def test_augment_prompt_phase2_with_missing_fields(self):
        """Test phase 2 augmentation handles missing fields gracefully"""
        original = "Flight EY123 on Jan 20th had a mechanical failure"
        collation = {
            "responses": {
                "crew_compliance": {
                    # Missing recommendation and confidence
                }
            }
        }
        
        augmented = augment_prompt_phase2(original, collation)
        
        # Should handle missing fields with N/A
        assert "CREW_COMPLIANCE" in augmented
        assert "N/A" in augmented


class TestRunAgentSafely:
    """Test run_agent_safely function"""
    
    @pytest.mark.asyncio
    async def test_run_agent_safely_success(self):
        """Test successful agent execution"""
        # Mock agent function
        async def mock_agent(payload, llm, mcp_tools):
            return {
                "agent": "test_agent",
                "recommendation": "Test recommendation",
                "confidence": 0.95,
                "reasoning": "Test reasoning",
                "data_sources": ["test"],
                "timestamp": datetime.now().isoformat()
            }
        
        # Mock LLM and tools
        mock_llm = Mock()
        mock_mcp_tools = []
        
        # Create payload
        payload = {
            "user_prompt": "Test prompt",
            "phase": "initial"
        }
        
        # Run agent
        result = await run_agent_safely(
            "test_agent",
            mock_agent,
            payload,
            mock_llm,
            mock_mcp_tools
        )
        
        # Verify result
        assert result["agent"] == "test_agent"
        assert result["status"] == "success"
        assert result["recommendation"] == "Test recommendation"
        assert result["confidence"] == 0.95
        assert "duration_seconds" in result
        assert result["duration_seconds"] > 0
    
    @pytest.mark.asyncio
    async def test_run_agent_safely_timeout(self):
        """Test agent timeout handling"""
        # Mock agent that takes too long
        async def slow_agent(payload, llm, mcp_tools):
            await asyncio.sleep(35)  # Longer than default timeout
            return {"agent": "slow_agent"}
        
        # Mock LLM and tools
        mock_llm = Mock()
        mock_mcp_tools = []
        
        # Create payload
        payload = {
            "user_prompt": "Test prompt",
            "phase": "initial"
        }
        
        # Run agent with short timeout for testing
        result = await run_agent_safely(
            "slow_agent",
            slow_agent,
            payload,
            mock_llm,
            mock_mcp_tools,
            timeout=1  # 1 second timeout for testing
        )
        
        # Verify timeout result
        assert result["status"] == "timeout"
        assert result["agent"] == "slow_agent"
        assert "timeout" in result["error"].lower()
        assert "duration_seconds" in result
        assert result["duration_seconds"] >= 1
    
    @pytest.mark.asyncio
    async def test_run_agent_safely_exception(self):
        """Test agent exception handling"""
        # Mock agent that raises exception
        async def error_agent(payload, llm, mcp_tools):
            raise ValueError("Test error message")
        
        # Mock LLM and tools
        mock_llm = Mock()
        mock_mcp_tools = []
        
        # Create payload
        payload = {
            "user_prompt": "Test prompt",
            "phase": "initial"
        }
        
        # Run agent
        result = await run_agent_safely(
            "error_agent",
            error_agent,
            payload,
            mock_llm,
            mock_mcp_tools
        )
        
        # Verify error result
        assert result["status"] == "error"
        assert result["agent"] == "error_agent"
        assert "Test error message" in result["error"]
        assert result["error_type"] == "ValueError"
        assert "duration_seconds" in result
    
    @pytest.mark.asyncio
    async def test_run_agent_safely_preserves_agent_status(self):
        """Test that agent-set status is preserved"""
        # Mock agent that sets its own status
        async def agent_with_status(payload, llm, mcp_tools):
            return {
                "agent": "test_agent",
                "status": "partial_success",
                "recommendation": "Partial recommendation",
                "confidence": 0.5,
                "reasoning": "Some data missing",
                "data_sources": ["test"],
                "timestamp": datetime.now().isoformat()
            }
        
        # Mock LLM and tools
        mock_llm = Mock()
        mock_mcp_tools = []
        
        # Create payload
        payload = {
            "user_prompt": "Test prompt",
            "phase": "initial"
        }
        
        # Run agent
        result = await run_agent_safely(
            "test_agent",
            agent_with_status,
            payload,
            mock_llm,
            mock_mcp_tools
        )
        
        # Verify agent's status is preserved
        assert result["status"] == "partial_success"
        assert result["agent"] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_run_agent_safely_adds_duration(self):
        """Test that duration is always added to result"""
        # Mock agent
        async def mock_agent(payload, llm, mcp_tools):
            await asyncio.sleep(0.1)  # Simulate some processing
            return {
                "agent": "test_agent",
                "recommendation": "Test",
                "confidence": 0.9,
                "reasoning": "Test",
                "data_sources": [],
                "timestamp": datetime.now().isoformat()
            }
        
        # Mock LLM and tools
        mock_llm = Mock()
        mock_mcp_tools = []
        
        # Create payload
        payload = {
            "user_prompt": "Test prompt",
            "phase": "initial"
        }
        
        # Run agent
        result = await run_agent_safely(
            "test_agent",
            mock_agent,
            payload,
            mock_llm,
            mock_mcp_tools
        )
        
        # Verify duration is present and reasonable
        assert "duration_seconds" in result
        assert result["duration_seconds"] >= 0.1
        assert result["duration_seconds"] < 1.0  # Should be quick


class TestAgentRegistry:
    """Test agent registry configuration"""
    
    def test_agent_registry_contains_all_agents(self):
        """Test that agent registry contains all 7 agents"""
        expected_agents = [
            "crew_compliance",
            "maintenance",
            "regulatory",
            "network",
            "guest_experience",
            "cargo",
            "finance"
        ]
        
        for agent_name in expected_agents:
            assert agent_name in AGENT_REGISTRY
            assert callable(AGENT_REGISTRY[agent_name])
    
    def test_safety_agents_configuration(self):
        """Test safety agents are correctly configured"""
        expected_safety = [
            "crew_compliance",
            "maintenance",
            "regulatory"
        ]
        
        safety_names = [name for name, _ in SAFETY_AGENTS]
        assert len(safety_names) == 3
        
        for agent_name in expected_safety:
            assert agent_name in safety_names
    
    def test_business_agents_configuration(self):
        """Test business agents are correctly configured"""
        expected_business = [
            "network",
            "guest_experience",
            "cargo",
            "finance"
        ]
        
        business_names = [name for name, _ in BUSINESS_AGENTS]
        assert len(business_names) == 4
        
        for agent_name in expected_business:
            assert agent_name in business_names
    
    def test_all_agents_accounted_for(self):
        """Test that safety + business = all agents"""
        safety_names = [name for name, _ in SAFETY_AGENTS]
        business_names = [name for name, _ in BUSINESS_AGENTS]
        
        all_agent_names = safety_names + business_names
        
        # Should have 7 total agents
        assert len(all_agent_names) == 7
        
        # Should match registry
        assert set(all_agent_names) == set(AGENT_REGISTRY.keys())


class TestOrchestratorInvariants:
    """Test orchestrator correctness properties"""
    
    def test_orchestrator_has_no_parsing_logic(self):
        """Test that orchestrator code contains no parsing logic"""
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for parsing-related patterns that should NOT exist
        forbidden_patterns = [
            "re.match",
            "re.search",
            "re.findall",
            ".split('EY')",
            "extract_flight_number",
            "parse_date",
            "validate_flight",
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not contain parsing logic: {pattern}"
    
    def test_orchestrator_has_no_database_queries(self):
        """Test that orchestrator code contains no database query logic"""
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for database query patterns that should NOT exist in orchestrator
        # (They should only exist in agents)
        forbidden_patterns = [
            "dynamodb.Table",
            ".query(",
            ".get_item(",
            ".scan(",
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not contain database queries: {pattern}"
    
    def test_augment_prompt_does_not_modify_content(self):
        """Test that prompt augmentation preserves original content"""
        test_prompts = [
            "Flight EY123 on Jan 20th had a mechanical failure",
            "EY456 yesterday was delayed due to weather",
            "Analyze flight 789 from AUH to LHR on 2026-01-20",
            "Flight EY999 @ 14:30 UTC - engine failure (critical)",
        ]
        
        for original in test_prompts:
            # Test phase 1
            augmented1 = augment_prompt_phase1(original)
            assert original in augmented1, \
                f"Phase 1 augmentation should preserve original: {original}"
            
            # Test phase 2
            collation = {"responses": {}}
            augmented2 = augment_prompt_phase2(original, collation)
            assert original in augmented2, \
                f"Phase 2 augmentation should preserve original: {original}"


class TestErrorHandling:
    """Test error handling in orchestrator"""
    
    @pytest.mark.asyncio
    async def test_run_agent_safely_handles_none_return(self):
        """Test handling of agent returning None"""
        async def none_agent(payload, llm, mcp_tools):
            return None
        
        mock_llm = Mock()
        mock_mcp_tools = []
        payload = {"user_prompt": "Test", "phase": "initial"}
        
        # Should handle None gracefully (will raise exception)
        result = await run_agent_safely(
            "none_agent",
            none_agent,
            payload,
            mock_llm,
            mock_mcp_tools
        )
        
        # Should return error status
        assert result["status"] == "error"
        assert result["agent"] == "none_agent"
    
    @pytest.mark.asyncio
    async def test_run_agent_safely_handles_invalid_return(self):
        """Test handling of agent returning invalid data"""
        async def invalid_agent(payload, llm, mcp_tools):
            return "not a dict"
        
        mock_llm = Mock()
        mock_mcp_tools = []
        payload = {"user_prompt": "Test", "phase": "initial"}
        
        # Should handle invalid return gracefully
        result = await run_agent_safely(
            "invalid_agent",
            invalid_agent,
            payload,
            mock_llm,
            mock_mcp_tools
        )
        
        # Should return error status
        assert result["status"] == "error"
        assert result["agent"] == "invalid_agent"


class TestPromptAugmentationInvariants:
    """Test invariants for prompt augmentation (Property 1)"""
    
    def test_phase1_augmentation_adds_instruction_only(self):
        """Test that phase 1 augmentation only adds instruction, no parsing"""
        original = "Flight EY123 on Jan 20th had a mechanical failure"
        augmented = augment_prompt_phase1(original)
        
        # Should contain original exactly
        assert original in augmented
        
        # Should add instruction
        assert len(augmented) > len(original)
        
        # Should not extract or modify flight info
        assert "EY123" in augmented  # Flight number preserved
        assert "Jan 20th" in augmented  # Date preserved
        assert "mechanical failure" in augmented  # Event preserved
    
    def test_phase2_augmentation_adds_context_only(self):
        """Test that phase 2 augmentation only adds context, no parsing"""
        original = "Flight EY123 on Jan 20th had a mechanical failure"
        collation = {
            "responses": {
                "crew_compliance": {
                    "recommendation": "Crew available",
                    "confidence": 0.95
                }
            }
        }
        
        augmented = augment_prompt_phase2(original, collation)
        
        # Should contain original exactly
        assert original in augmented
        
        # Should add other recommendations
        assert "Crew available" in augmented
        
        # Should not extract or modify flight info
        assert "EY123" in augmented  # Flight number preserved
        assert "Jan 20th" in augmented  # Date preserved
        assert "mechanical failure" in augmented  # Event preserved
    
    def test_augmentation_preserves_unicode(self):
        """Test that augmentation preserves unicode characters"""
        original = "Flight EY123 from AUH → LHR delayed ✈️"
        augmented = augment_prompt_phase1(original)
        
        # Should preserve unicode
        assert "→" in augmented
        assert "✈️" in augmented
        assert original in augmented
    
    def test_augmentation_preserves_whitespace(self):
        """Test that augmentation preserves whitespace in original"""
        original = "Flight  EY123   on   Jan 20th"  # Multiple spaces
        augmented = augment_prompt_phase1(original)
        
        # Should preserve exact whitespace
        assert original in augmented



class TestProperty1InstructionAugmentationInvariant:
    """
    Property-Based Tests for Property 1: Orchestrator Instruction Augmentation Invariant
    
    Feature: skymarshal-multi-round-orchestration
    Property 1: Orchestrator Instruction Augmentation Invariant
    Validates: Requirements 1.6, 1.7, 9.2, 9.3, 9.4
    
    For all user prompts p, the orchestrator SHALL augment p with phase-specific 
    instructions but NOT parse or extract data:
    
    ∀ prompt p, ∀ agent a, ∀ phase ph:
      orchestrator.invoke(a, p, ph) →
      a.receives(p + instruction(ph)) ∧
      user_content(p) == original_prompt ∧
      orchestrator.parses(p) = false
    
    Test Strategy: Verify that agents receive the user's original prompt plus 
    instructions, with no parsing, extraction, or data modification of the user's content.
    """
    
    @given(user_prompt=st.text(min_size=10, max_size=500))
    @settings(max_examples=100, deadline=None)
    def test_phase1_augmentation_preserves_original_content(self, user_prompt):
        """
        Property 1.1: Phase 1 augmentation preserves original prompt content
        
        For any user prompt p, augment_prompt_phase1(p) should contain p exactly
        without any parsing, extraction, or modification of the user's content.
        
        Validates: Requirements 1.6, 9.2, 9.3
        """
        # Augment the prompt
        augmented = augment_prompt_phase1(user_prompt)
        
        # Property: Original prompt must be preserved exactly
        assert user_prompt in augmented, \
            f"Phase 1 augmentation must preserve original prompt exactly"
        
        # Property: Augmented prompt should be longer (instruction added)
        assert len(augmented) >= len(user_prompt), \
            f"Phase 1 augmentation should add instructions"
        
        # Property: If original is non-empty, augmented should contain instruction
        if user_prompt.strip():
            assert "Please analyze this disruption" in augmented, \
                f"Phase 1 augmentation should add analysis instruction"
            assert "initial recommendation" in augmented, \
                f"Phase 1 augmentation should mention initial recommendation"
    
    @given(user_prompt=st.text(min_size=10, max_size=500))
    @settings(max_examples=100, deadline=None)
    def test_phase2_augmentation_preserves_original_content(self, user_prompt):
        """
        Property 1.2: Phase 2 augmentation preserves original prompt content
        
        For any user prompt p and collation c, augment_prompt_phase2(p, c) should 
        contain p exactly without any parsing, extraction, or modification.
        
        Validates: Requirements 1.6, 9.4
        """
        # Create a sample collation
        collation = {
            "responses": {
                "crew_compliance": {
                    "recommendation": "Test recommendation",
                    "confidence": 0.95
                }
            }
        }
        
        # Augment the prompt
        augmented = augment_prompt_phase2(user_prompt, collation)
        
        # Property: Original prompt must be preserved exactly
        assert user_prompt in augmented, \
            f"Phase 2 augmentation must preserve original prompt exactly"
        
        # Property: Augmented prompt should be longer (instruction + collation added)
        assert len(augmented) >= len(user_prompt), \
            f"Phase 2 augmentation should add instructions and collation"
        
        # Property: If original is non-empty, augmented should contain instruction
        if user_prompt.strip():
            assert "Review other agents' recommendations" in augmented, \
                f"Phase 2 augmentation should add review instruction"
            assert "revise if needed" in augmented, \
                f"Phase 2 augmentation should mention revision"
    
    @given(
        user_prompt=st.text(
            min_size=20,
            max_size=200,
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
                whitelist_characters='@#$%&*()[]{}:;,.!?-_'
            )
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_augmentation_preserves_special_characters(self, user_prompt):
        """
        Property 1.3: Augmentation preserves special characters and formatting
        
        For any user prompt p containing special characters, augmentation should
        preserve all characters exactly without escaping or modification.
        
        Validates: Requirements 1.6, 9.2
        """
        # Test phase 1
        augmented1 = augment_prompt_phase1(user_prompt)
        assert user_prompt in augmented1, \
            f"Phase 1 must preserve special characters: {user_prompt[:50]}"
        
        # Test phase 2
        collation = {"responses": {}}
        augmented2 = augment_prompt_phase2(user_prompt, collation)
        assert user_prompt in augmented2, \
            f"Phase 2 must preserve special characters: {user_prompt[:50]}"
    
    @given(
        flight_number=st.from_regex(r'EY[0-9]{3,4}', fullmatch=True),
        date_str=st.sampled_from([
            "Jan 20th", "January 20th 2026", "20/01/2026", 
            "2026-01-20", "yesterday", "today"
        ]),
        event=st.sampled_from([
            "mechanical failure", "weather delay", "crew shortage",
            "technical issues", "engine failure"
        ])
    )
    @settings(max_examples=50, deadline=None)
    def test_augmentation_preserves_flight_information(self, flight_number, date_str, event):
        """
        Property 1.4: Augmentation preserves flight information without extraction
        
        For any prompt containing flight number, date, and event, augmentation
        should preserve all information exactly without parsing or extracting.
        
        Validates: Requirements 1.6, 1.7, 1.8
        """
        # Construct a realistic prompt
        user_prompt = f"Flight {flight_number} on {date_str} had a {event}"
        
        # Test phase 1
        augmented1 = augment_prompt_phase1(user_prompt)
        
        # Property: All flight information must be preserved
        assert flight_number in augmented1, \
            f"Flight number must be preserved: {flight_number}"
        assert date_str in augmented1, \
            f"Date must be preserved: {date_str}"
        assert event in augmented1, \
            f"Event must be preserved: {event}"
        
        # Property: Original prompt must be intact
        assert user_prompt in augmented1, \
            f"Complete original prompt must be preserved"
        
        # Test phase 2
        collation = {"responses": {}}
        augmented2 = augment_prompt_phase2(user_prompt, collation)
        
        # Property: All flight information must be preserved in phase 2
        assert flight_number in augmented2, \
            f"Flight number must be preserved in phase 2: {flight_number}"
        assert date_str in augmented2, \
            f"Date must be preserved in phase 2: {date_str}"
        assert event in augmented2, \
            f"Event must be preserved in phase 2: {event}"
    
    @given(
        whitespace_count=st.integers(min_value=1, max_value=5),
        word1=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        word2=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
    )
    @settings(max_examples=30, deadline=None)
    def test_augmentation_preserves_whitespace(self, whitespace_count, word1, word2):
        """
        Property 1.5: Augmentation preserves whitespace in original prompt
        
        For any prompt with specific whitespace patterns, augmentation should
        preserve the exact whitespace without normalization.
        
        Validates: Requirements 1.6, 9.2
        """
        # Create prompt with specific whitespace
        spaces = " " * whitespace_count
        user_prompt = f"{word1}{spaces}{word2}"
        
        # Test phase 1
        augmented1 = augment_prompt_phase1(user_prompt)
        assert user_prompt in augmented1, \
            f"Whitespace must be preserved: '{user_prompt}'"
        
        # Test phase 2
        collation = {"responses": {}}
        augmented2 = augment_prompt_phase2(user_prompt, collation)
        assert user_prompt in augmented2, \
            f"Whitespace must be preserved in phase 2: '{user_prompt}'"
    
    def test_orchestrator_code_has_no_parsing_logic(self):
        """
        Property 1.6: Orchestrator code contains no parsing logic
        
        The orchestrator should not contain any parsing, extraction, or validation
        logic. All such operations should be performed by agents.
        
        Validates: Requirements 1.6, 1.7, 9.2
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for parsing-related patterns that should NOT exist
        forbidden_patterns = [
            "re.match",
            "re.search",
            "re.findall",
            ".split('EY')",
            "extract_flight_number",
            "parse_date",
            "validate_flight",
            "parse_flight",
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not contain parsing logic: {pattern}"
    
    def test_orchestrator_code_has_no_database_queries(self):
        """
        Property 1.7: Orchestrator code contains no database query logic
        
        The orchestrator should not perform any database queries. All database
        access should be performed by agents using their tools.
        
        Validates: Requirements 1.6, 1.7, 9.2
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for database query patterns that should NOT exist in orchestrator
        forbidden_patterns = [
            "dynamodb.Table",
            ".query(",
            ".get_item(",
            ".scan(",
            "boto3.resource('dynamodb')",
            "boto3.client('dynamodb')",
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not contain database queries: {pattern}"
    
    @given(
        user_prompt=st.text(min_size=20, max_size=200),
        num_agents=st.integers(min_value=1, max_value=7)
    )
    @settings(max_examples=30, deadline=None)
    def test_phase2_augmentation_includes_collation(self, user_prompt, num_agents):
        """
        Property 1.8: Phase 2 augmentation includes other agents' recommendations
        
        For any prompt p and collation c with n agents, augment_prompt_phase2(p, c)
        should include all n agent recommendations while preserving p.
        
        Validates: Requirements 9.4, 10.1, 10.2
        """
        # Create collation with multiple agents
        agent_names = ["crew_compliance", "maintenance", "regulatory", 
                      "network", "guest_experience", "cargo", "finance"]
        
        collation = {
            "responses": {
                agent_names[i]: {
                    "recommendation": f"Recommendation from {agent_names[i]}",
                    "confidence": 0.9
                }
                for i in range(min(num_agents, len(agent_names)))
            }
        }
        
        # Augment prompt
        augmented = augment_prompt_phase2(user_prompt, collation)
        
        # Property: Original prompt preserved
        assert user_prompt in augmented, \
            f"Original prompt must be preserved"
        
        # Property: All agent recommendations included
        for agent_name in collation["responses"].keys():
            assert agent_name.upper() in augmented, \
                f"Agent {agent_name} should be included in collation"
            assert collation["responses"][agent_name]["recommendation"] in augmented, \
                f"Recommendation from {agent_name} should be included"
    
    @given(user_prompt=st.text(min_size=10, max_size=500))
    @settings(max_examples=50, deadline=None)
    def test_augmentation_is_deterministic(self, user_prompt):
        """
        Property 1.9: Augmentation is deterministic
        
        For any prompt p, multiple calls to augment_prompt_phase1(p) should
        produce identical results (deterministic behavior).
        
        Validates: Requirements 9.2, 9.3
        """
        # Call augmentation multiple times
        result1 = augment_prompt_phase1(user_prompt)
        result2 = augment_prompt_phase1(user_prompt)
        result3 = augment_prompt_phase1(user_prompt)
        
        # Property: All results should be identical
        assert result1 == result2 == result3, \
            f"Augmentation should be deterministic"
    
    @given(
        user_prompt=st.text(min_size=10, max_size=200),
        has_binding_constraints=st.booleans()
    )
    @settings(max_examples=30, deadline=None)
    def test_phase2_includes_binding_constraints(self, user_prompt, has_binding_constraints):
        """
        Property 1.10: Phase 2 augmentation includes binding constraints
        
        For any collation with binding constraints, augment_prompt_phase2 should
        include those constraints in the augmented prompt.
        
        Validates: Requirements 10.3, 11.3
        """
        # Create collation with optional binding constraints
        collation = {
            "responses": {
                "maintenance": {
                    "recommendation": "Aircraft needs inspection",
                    "confidence": 0.95,
                    "binding_constraints": ["Must inspect engine"] if has_binding_constraints else []
                }
            }
        }
        
        # Augment prompt
        augmented = augment_prompt_phase2(user_prompt, collation)
        
        # Property: Original prompt preserved
        assert user_prompt in augmented
        
        # Property: Binding constraints included if present
        if has_binding_constraints:
            assert "Binding Constraints" in augmented, \
                f"Binding constraints should be included when present"
            assert "Must inspect engine" in augmented, \
                f"Specific binding constraint should be included"


class TestProperty2AgentAutonomy:
    """
    Property-Based Tests for Property 2: Agent Autonomy Property
    
    Feature: skymarshal-multi-round-orchestration
    Property 2: Agent Autonomy Property
    Validates: Requirements 1.7, 2.1, 2.7
    
    All data extraction and lookups SHALL be performed by agents using LangChain 
    structured output, not the orchestrator:
    
    ∀ operation o ∈ {parse, extract, validate, lookup}:
      orchestrator.performs(o) = false ∧
      agent.performs(o) = true ∧
      agent.uses_structured_output(o) = true
    
    Test Strategy: Verify orchestrator code contains no parsing logic, validation 
    logic, or database query calls. Verify agents use `with_structured_output()` 
    for data extraction.
    """
    
    def test_orchestrator_has_no_parsing_functions(self):
        """
        Property 2.1: Orchestrator contains no parsing functions
        
        The orchestrator should not define or use any functions for parsing
        flight numbers, dates, or disruption events from user prompts.
        
        Validates: Requirements 1.6, 1.7, 9.2
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for parsing function definitions that should NOT exist
        forbidden_function_patterns = [
            "def parse_flight_number",
            "def extract_flight_number",
            "def parse_date",
            "def extract_date",
            "def validate_flight_number",
            "def validate_date",
            "def parse_disruption",
            "def extract_disruption",
            "def parse_prompt",
            "def extract_flight_info",
        ]
        
        for pattern in forbidden_function_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not define parsing function: {pattern}"
    
    def test_orchestrator_has_no_regex_imports(self):
        """
        Property 2.2: Orchestrator does not import regex module
        
        The orchestrator should not import the 're' module since it should
        not perform any pattern matching or parsing operations.
        
        Validates: Requirements 1.6, 1.7
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for regex imports that should NOT exist
        forbidden_imports = [
            "import re",
            "from re import",
        ]
        
        for pattern in forbidden_imports:
            assert pattern not in source_code, \
                f"Orchestrator should not import regex module: {pattern}"
    
    def test_orchestrator_has_no_validation_logic(self):
        """
        Property 2.3: Orchestrator contains no validation logic
        
        The orchestrator should not validate flight numbers, dates, or any
        other user input. All validation is performed by agents.
        
        Validates: Requirements 1.6, 1.7, 2.1
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for validation patterns that should NOT exist
        forbidden_validation_patterns = [
            "if not flight_number",
            "if not date",
            "raise ValueError",
            "raise ValidationError",
            "validate(",
            "is_valid_flight",
            "is_valid_date",
            "check_flight_format",
            "check_date_format",
        ]
        
        for pattern in forbidden_validation_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not contain validation logic: {pattern}"
    
    def test_orchestrator_has_no_database_imports(self):
        """
        Property 2.4: Orchestrator does not import database modules
        
        The orchestrator should not import boto3 or DynamoDB-related modules
        since it should not perform any database queries.
        
        Validates: Requirements 1.6, 2.7, 9.2
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for database imports that should NOT exist in orchestrator
        forbidden_db_imports = [
            "import boto3",
            "from boto3 import",
            "from database.dynamodb import",
            "from database.tools import",
        ]
        
        for pattern in forbidden_db_imports:
            assert pattern not in source_code, \
                f"Orchestrator should not import database modules: {pattern}"
    
    def test_orchestrator_has_no_database_queries(self):
        """
        Property 2.5: Orchestrator contains no database query calls
        
        The orchestrator should not call any DynamoDB query methods.
        All database access is performed by agents using their tools.
        
        Validates: Requirements 1.6, 2.7, 9.2
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for database query patterns that should NOT exist
        forbidden_query_patterns = [
            ".query(",
            ".get_item(",
            ".scan(",
            ".put_item(",
            ".update_item(",
            ".delete_item(",
            "dynamodb.Table",
            "boto3.resource('dynamodb')",
            "boto3.client('dynamodb')",
        ]
        
        for pattern in forbidden_query_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not contain database queries: {pattern}"
    
    def test_orchestrator_has_no_flight_lookup_logic(self):
        """
        Property 2.6: Orchestrator contains no flight lookup logic
        
        The orchestrator should not perform flight lookups or retrieve
        flight_id from the database. This is the responsibility of agents.
        
        Validates: Requirements 2.1, 2.2, 2.7
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for flight lookup patterns that should NOT exist
        forbidden_lookup_patterns = [
            "lookup_flight",
            "get_flight",
            "query_flight",
            "find_flight",
            "search_flight",
            "flight_id =",
            "retrieve_flight",
        ]
        
        for pattern in forbidden_lookup_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not contain flight lookup logic: {pattern}"
    
    def test_orchestrator_only_passes_prompts(self):
        """
        Property 2.7: Orchestrator only passes prompts to agents
        
        The orchestrator should only pass natural language prompts to agents,
        not extracted or parsed data structures.
        
        Validates: Requirements 1.6, 9.2, 9.4
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Verify orchestrator uses user_prompt in payloads
        assert "user_prompt" in source_code, \
            "Orchestrator should pass user_prompt to agents"
        
        # Check that orchestrator does NOT pass extracted fields
        forbidden_payload_fields = [
            '"flight_number":',
            '"date":',
            '"disruption_event":',
            '"flight_id":',
            '"extracted_data":',
        ]
        
        # These patterns should not appear in payload construction
        for pattern in forbidden_payload_fields:
            # Allow them in comments or docstrings, but not in actual code
            lines = source_code.split('\n')
            code_lines = [
                line for line in lines 
                if not line.strip().startswith('#') 
                and not line.strip().startswith('"""')
                and not line.strip().startswith("'''")
            ]
            code_only = '\n'.join(code_lines)
            
            assert pattern not in code_only, \
                f"Orchestrator should not pass extracted fields in payload: {pattern}"
    
    @given(user_prompt=st.text(min_size=20, max_size=500))
    @settings(max_examples=50, deadline=None)
    def test_orchestrator_preserves_prompt_for_agents(self, user_prompt):
        """
        Property 2.8: Orchestrator preserves user prompt for agent processing
        
        For any user prompt p, the orchestrator should pass p to agents
        without extracting or parsing any fields from it.
        
        Validates: Requirements 1.6, 1.7, 9.2
        """
        # Augment prompt (what orchestrator does)
        augmented_phase1 = augment_prompt_phase1(user_prompt)
        
        # Property: Original prompt must be preserved
        assert user_prompt in augmented_phase1, \
            f"Orchestrator must preserve original prompt for agents"
        
        # Property: No extracted fields should be added
        # The augmented prompt should only contain the original + instruction
        # It should NOT contain structured data like {"flight_number": "EY123"}
        assert "{" not in augmented_phase1 or user_prompt.count("{") == augmented_phase1.count("{"), \
            f"Orchestrator should not add structured data to prompt"
    
    def test_agents_use_structured_output_pattern(self):
        """
        Property 2.9: Agents use LangChain structured output for extraction
        
        Agent code should use LangChain's with_structured_output() pattern
        with Pydantic models for data extraction, not custom parsing.
        
        Validates: Requirements 1.7, 2.1
        """
        # Check that schemas.py defines Pydantic models for structured output
        schemas_path = Path(__file__).parent.parent / "src" / "agents" / "schemas.py"
        with open(schemas_path, 'r') as f:
            schemas_code = f.read()
        
        # Verify Pydantic BaseModel is imported
        assert "from pydantic import BaseModel" in schemas_code, \
            "Schemas should use Pydantic BaseModel"
        
        # Verify output schemas are defined
        expected_schemas = [
            "class CrewComplianceOutput",
            "class MaintenanceOutput",
            "class RegulatoryOutput",
            "class NetworkOutput",
            "class GuestExperienceOutput",
            "class CargoOutput",
            "class FinanceOutput",
        ]
        
        for schema in expected_schemas:
            assert schema in schemas_code, \
                f"Schemas should define {schema} for structured output"
    
    def test_agents_do_not_use_custom_parsing(self):
        """
        Property 2.10: Agents do not use custom parsing functions
        
        Agent code should not define custom parsing functions. All extraction
        should be handled by LangChain structured output.
        
        Validates: Requirements 1.7, 2.1
        """
        # Check agent files for custom parsing patterns
        agents_dir = Path(__file__).parent.parent / "src" / "agents"
        agent_subdirs = [
            "crew_compliance",
            "maintenance", 
            "regulatory",
            "network",
            "guest_experience",
            "cargo",
            "finance"
        ]
        
        forbidden_parsing_patterns = [
            "def parse_flight_number",
            "def extract_flight_number",
            "def parse_date",
            "def extract_date",
            "re.match",
            "re.search",
            "re.findall",
            ".split('EY')",
        ]
        
        for agent_dir in agent_subdirs:
            agent_file = agents_dir / agent_dir / "agent.py"
            if agent_file.exists():
                with open(agent_file, 'r') as f:
                    agent_code = f.read()
                
                for pattern in forbidden_parsing_patterns:
                    assert pattern not in agent_code, \
                        f"Agent {agent_dir} should not use custom parsing: {pattern}"
    
    def test_orchestrator_functions_are_pure_coordinators(self):
        """
        Property 2.11: Orchestrator functions are pure coordinators
        
        The orchestrator's phase functions should only coordinate agent
        invocations and collate responses, not process data.
        
        Validates: Requirements 9.1, 9.2, 9.4
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Verify phase functions exist
        assert "async def phase1_initial_recommendations" in source_code, \
            "Orchestrator should define phase1_initial_recommendations"
        assert "async def phase2_revision_round" in source_code, \
            "Orchestrator should define phase2_revision_round"
        assert "async def phase3_arbitration" in source_code, \
            "Orchestrator should define phase3_arbitration"
        
        # Verify orchestrator uses asyncio for parallel execution
        assert "asyncio.gather" in source_code or "asyncio.create_task" in source_code, \
            "Orchestrator should use asyncio for parallel agent execution"
    
    @given(
        flight_number=st.from_regex(r'EY[0-9]{3,4}', fullmatch=True),
        date_str=st.sampled_from([
            "Jan 20th", "January 20th 2026", "20/01/2026", 
            "2026-01-20", "yesterday"
        ]),
    )
    @settings(max_examples=30, deadline=None)
    def test_orchestrator_does_not_extract_flight_info(self, flight_number, date_str):
        """
        Property 2.12: Orchestrator does not extract flight information
        
        For any prompt containing flight information, the orchestrator should
        pass it to agents without extracting flight_number or date.
        
        Validates: Requirements 1.6, 1.7, 2.1
        """
        # Create a realistic prompt
        user_prompt = f"Flight {flight_number} on {date_str} had a mechanical failure"
        
        # Augment prompt (what orchestrator does)
        augmented = augment_prompt_phase1(user_prompt)
        
        # Property: Flight number should remain in natural language form
        assert flight_number in augmented, \
            f"Flight number should remain in prompt: {flight_number}"
        
        # Property: Date should remain in natural language form
        assert date_str in augmented, \
            f"Date should remain in prompt: {date_str}"
        
        # Property: No structured extraction should occur
        # The augmented prompt should not contain JSON or structured data
        assert not augmented.startswith("{"), \
            f"Orchestrator should not create structured data"
        assert not augmented.startswith("["), \
            f"Orchestrator should not create structured data"
    
    def test_orchestrator_has_no_pydantic_extraction_models(self):
        """
        Property 2.13: Orchestrator does not define Pydantic extraction models
        
        The orchestrator should not define Pydantic models for extracting
        flight information. Only agents should define such models.
        
        Validates: Requirements 1.7, 2.1
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for Pydantic model definitions that should NOT exist
        forbidden_model_patterns = [
            "class FlightInfo(BaseModel)",
            "class FlightExtraction(BaseModel)",
            "class DisruptionInfo(BaseModel)",
            "class UserInput(BaseModel)",
        ]
        
        for pattern in forbidden_model_patterns:
            assert pattern not in source_code, \
                f"Orchestrator should not define extraction models: {pattern}"
    
    def test_orchestrator_does_not_use_with_structured_output(self):
        """
        Property 2.14: Orchestrator does not use with_structured_output()
        
        The orchestrator should not use LangChain's with_structured_output()
        method since it should not extract data from prompts.
        
        Validates: Requirements 1.6, 1.7, 2.1
        """
        # Read main.py source code
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        # Check for with_structured_output usage that should NOT exist
        assert "with_structured_output" not in source_code, \
            "Orchestrator should not use with_structured_output()"
        
        assert ".with_structured_output(" not in source_code, \
            "Orchestrator should not call with_structured_output()"
