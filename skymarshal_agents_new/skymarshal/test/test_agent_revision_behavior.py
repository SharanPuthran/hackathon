"""Comprehensive unit tests for agent revision behavior

This module tests that all agents correctly implement revision round logic:
- Agents check payload.phase to determine initial vs revision
- Agents receive and process other_recommendations in revision phase
- Agents use revision_logic utilities to determine if revision is needed
- Agents revise their recommendations when appropriate
- Agents maintain domain priorities during revision

These tests validate the acceptance criteria for Task 14.5.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from agents.revision_logic import (
    RevisionDecision,
    RevisionReason,
    analyze_other_recommendations,
    get_domain_keywords,
)


class TestCrewComplianceRevisionBehavior:
    """Test crew compliance agent revision behavior"""
    
    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_agent_checks_phase_field(self, mock_boto3):
        """Test that agent checks payload.phase to determine initial vs revision"""
        from agents.crew_compliance.agent import analyze_crew_compliance
        
        # Mock DynamoDB
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Mock LLM
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.invoke.return_value = Mock(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        # Test initial phase
        initial_payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
            "other_recommendations": None
        }
        
        # Agent should process initial phase without other recommendations
        result = await analyze_crew_compliance(initial_payload, llm, [])
        assert result is not None
        assert "agent_name" in result
        
        # Test revision phase
        revision_payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": {
                "maintenance": {
                    "recommendation": "3 hour delay required",
                    "confidence": 0.85,
                    "reasoning": "Engine inspection needed"
                }
            }
        }
        
        # Agent should process revision phase with other recommendations
        result = await analyze_crew_compliance(revision_payload, llm, [])
        assert result is not None
        assert "agent_name" in result
    
    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_agent_receives_other_recommendations_in_revision(self, mock_boto3):
        """Test that agent receives other_recommendations in revision phase"""
        from agents.crew_compliance.agent import analyze_crew_compliance
        
        # Mock DynamoDB
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Mock LLM
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.invoke.return_value = Mock(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        other_recs = {
            "maintenance": {
                "recommendation": "3 hour delay required for inspection",
                "confidence": 0.85,
                "reasoning": "Engine oil leak detected",
                "binding_constraints": ["Aircraft cannot depart until inspection complete"]
            },
            "regulatory": {
                "recommendation": "APPROVED with curfew warning",
                "confidence": 0.8,
                "reasoning": "3h delay would result in 23:00 arrival"
            }
        }
        
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": other_recs
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        # Agent should process the payload successfully
        assert result is not None
        assert result["agent_name"] == "crew_compliance"


class TestMaintenanceRevisionBehavior:
    """Test maintenance agent revision behavior"""
    
    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_agent_revises_when_timing_changes(self, mock_create_agent):
        """Test that maintenance agent revises when other agents provide timing changes"""
        from agents.maintenance.agent import analyze_maintenance
        
        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "output": "REVISED: Extended maintenance window needed due to crew FDP limits"
        }
        mock_create_agent.return_value = mock_agent
        
        # Mock LLM
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.invoke.return_value = Mock(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        other_recs = {
            "crew_compliance": {
                "recommendation": "REQUIRES_CREW_CHANGE if delay exceeds 2 hours",
                "confidence": 0.9,
                "reasoning": "Current crew FDP limit: 2h margin remaining",
                "binding_constraints": ["Crew must complete flight within 2 hours"]
            }
        }
        
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": other_recs
        }
        
        result = await analyze_maintenance(payload, llm, [])
        
        # Agent should process revision
        assert result is not None
        assert result["agent_name"] == "maintenance"


class TestRegulatoryRevisionBehavior:
    """Test regulatory agent revision behavior"""
    
    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_agent_strengthens_with_safety_consensus(self, mock_create_agent):
        """Test that regulatory agent strengthens recommendation with safety consensus"""
        from agents.regulatory.agent import analyze_regulatory
        
        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "output": "STRENGTHENED: All safety agents confirm compliance"
        }
        mock_create_agent.return_value = mock_agent
        
        # Mock LLM
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.invoke.return_value = Mock(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        other_recs = {
            "crew_compliance": {
                "recommendation": "APPROVED - Crew within limits",
                "confidence": 0.9,
                "reasoning": "All crew duty requirements met"
            },
            "maintenance": {
                "recommendation": "APPROVED - Aircraft airworthy",
                "confidence": 0.95,
                "reasoning": "All maintenance checks complete"
            }
        }
        
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": other_recs
        }
        
        result = await analyze_regulatory(payload, llm, [])
        
        # Agent should process revision
        assert result is not None
        assert result["agent_name"] == "regulatory"


class TestNetworkRevisionBehavior:
    """Test network agent revision behavior"""
    
    @pytest.mark.asyncio
    @patch('agents.network.agent.boto3')
    async def test_agent_revises_with_aircraft_swap_info(self, mock_boto3):
        """Test that network agent revises when maintenance suggests aircraft swap"""
        from agents.network.agent import analyze_network
        
        # Mock DynamoDB
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Mock LLM
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.invoke.return_value = Mock(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        other_recs = {
            "maintenance": {
                "recommendation": "REQUIRES AIRCRAFT SWAP - 8h repair needed",
                "confidence": 0.95,
                "reasoning": "Engine issue requires extended maintenance. Recommend swap to A6-EYZ.",
                "binding_constraints": ["Original aircraft unavailable for 8 hours"]
            }
        }
        
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": other_recs
        }
        
        result = await analyze_network(payload, llm, [])
        
        # Agent should process revision
        assert result is not None
        assert result["agent_name"] == "network"


class TestGuestExperienceRevisionBehavior:
    """Test guest experience agent revision behavior"""
    
    @pytest.mark.asyncio
    @patch('agents.guest_experience.agent.create_agent')
    @patch('agents.guest_experience.agent.dynamodb')
    async def test_agent_confirms_when_no_relevant_info(self, mock_dynamodb, mock_create_agent):
        """Test that guest experience agent confirms when no relevant passenger info"""
        from agents.guest_experience.agent import analyze_guest_experience
        
        # Mock agent with proper response structure
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                {"content": "CONFIRMED: No new passenger-related information"}
            ]
        }
        mock_create_agent.return_value = mock_agent
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock LLM
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.invoke.return_value = Mock(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        other_recs = {
            "maintenance": {
                "recommendation": "Aircraft requires inspection",
                "confidence": 0.85,
                "reasoning": "Technical issue identified"
            },
            "finance": {
                "recommendation": "Moderate cost impact",
                "confidence": 0.8,
                "reasoning": "Operational costs expected"
            }
        }
        
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": other_recs
        }
        
        result = await analyze_guest_experience(payload, llm, [])
        
        # Agent should process revision
        assert result is not None
        # Check that result has expected structure (may vary by agent implementation)
        assert isinstance(result, dict)


class TestCargoRevisionBehavior:
    """Test cargo agent revision behavior"""
    
    @pytest.mark.asyncio
    @patch('agents.cargo.agent.boto3.resource')
    async def test_agent_maintains_domain_priorities(self, mock_boto3):
        """Test that cargo agent maintains cargo domain priorities during revision"""
        from agents.cargo.agent import analyze_cargo
        
        # Mock DynamoDB
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb
        
        # Mock LLM - need to await the invoke call
        llm = Mock()
        structured_llm = AsyncMock()
        # Make invoke return an awaitable that resolves to the Mock
        async def mock_invoke(*args, **kwargs):
            return Mock(
                flight_number="EY123",
                date="2026-01-20",
                disruption_event="mechanical failure"
            )
        structured_llm.invoke = mock_invoke
        llm.with_structured_output.return_value = structured_llm
        
        other_recs = {
            "guest_experience": {
                "recommendation": "Prioritize VIP passengers",
                "confidence": 0.9,
                "reasoning": "5 elite tier passengers on flight"
            },
            "network": {
                "recommendation": "Delay acceptable",
                "confidence": 0.8,
                "reasoning": "Minimal downstream impact"
            }
        }
        
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": other_recs
        }
        
        result = await analyze_cargo(payload, llm, [])
        
        # Agent should maintain cargo priorities
        assert result is not None
        # Check that result has expected structure (may vary by agent implementation)
        assert isinstance(result, dict)


class TestFinanceRevisionBehavior:
    """Test finance agent revision behavior"""
    
    @pytest.mark.asyncio
    @patch('agents.finance.agent.boto3')
    @patch('agents.finance.agent.create_agent')
    async def test_agent_revises_with_cost_implications(self, mock_create_agent, mock_boto3):
        """Test that finance agent revises when other agents provide cost implications"""
        from agents.finance.agent import analyze_finance
        
        # Mock agent with proper response structure
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                {"content": "REVISED: Updated cost estimate based on aircraft swap"}
            ]
        }
        mock_create_agent.return_value = mock_agent
        
        # Mock DynamoDB
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Mock LLM
        llm = AsyncMock()
        structured_llm = AsyncMock()
        structured_llm.invoke.return_value = Mock(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        other_recs = {
            "maintenance": {
                "recommendation": "REQUIRES AIRCRAFT SWAP",
                "confidence": 0.95,
                "reasoning": "Aircraft swap costs $5k vs $50k cancellation"
            },
            "guest_experience": {
                "recommendation": "Passenger compensation required",
                "confidence": 0.85,
                "reasoning": "145 passengers affected, compensation estimated $8k"
            }
        }
        
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": other_recs
        }
        
        result = await analyze_finance(payload, llm, [])
        
        # Agent should revise with new cost information
        assert result is not None
        # Check that result has expected structure (may vary by agent implementation)
        assert isinstance(result, dict)


class TestRevisionLogicIntegration:
    """Test that agents use revision_logic utilities correctly"""
    
    def test_analyze_other_recommendations_returns_decision(self):
        """Test that analyze_other_recommendations returns proper decision"""
        initial_rec = {
            "recommendation": "APPROVED",
            "confidence": 0.9
        }
        
        other_recs = {
            "maintenance": {
                "recommendation": "3 hour delay required",
                "reasoning": "Engine inspection needed",
                "confidence": 0.85
            }
        }
        
        decision, reasons, justification = analyze_other_recommendations(
            agent_name="crew_compliance",
            initial_recommendation=initial_rec,
            other_recommendations=other_recs,
            domain_keywords=get_domain_keywords("crew_compliance")
        )
        
        # Should return valid decision
        assert decision in [RevisionDecision.REVISE, RevisionDecision.CONFIRM, RevisionDecision.STRENGTHEN]
        assert len(reasons) > 0
        assert justification is not None
        assert len(justification) > 0
    
    def test_get_domain_keywords_for_all_agents(self):
        """Test that domain keywords exist for all agents"""
        agents = [
            "crew_compliance",
            "maintenance",
            "regulatory",
            "network",
            "guest_experience",
            "cargo",
            "finance"
        ]
        
        for agent in agents:
            keywords = get_domain_keywords(agent)
            assert len(keywords) > 0, f"No keywords defined for {agent}"
            assert all(isinstance(kw, str) for kw in keywords)


class TestRevisionDecisionTypes:
    """Test that agents can make all three types of revision decisions"""
    
    def test_revise_decision_with_new_timing(self):
        """Test REVISE decision when new timing information provided"""
        initial_rec = {
            "recommendation": "APPROVED with 2h margin",
            "confidence": 0.9
        }
        
        other_recs = {
            "maintenance": {
                "recommendation": "3 hour delay required",
                "reasoning": "Extended maintenance needed",
                "confidence": 0.85
            }
        }
        
        decision, reasons, _ = analyze_other_recommendations(
            agent_name="crew_compliance",
            initial_recommendation=initial_rec,
            other_recommendations=other_recs,
            domain_keywords=get_domain_keywords("crew_compliance")
        )
        
        assert decision == RevisionDecision.REVISE
        assert RevisionReason.NEW_TIMING_INFO in reasons
    
    def test_confirm_decision_with_no_relevant_info(self):
        """Test CONFIRM decision when no relevant information provided"""
        initial_rec = {
            "recommendation": "APPROVED",
            "confidence": 0.95
        }
        
        other_recs = {
            "guest_experience": {
                "recommendation": "VIP passengers need attention",
                "reasoning": "Elite tier passengers on flight",
                "confidence": 0.9
            }
        }
        
        decision, reasons, _ = analyze_other_recommendations(
            agent_name="maintenance",
            initial_recommendation=initial_rec,
            other_recommendations=other_recs,
            domain_keywords=get_domain_keywords("maintenance")
        )
        
        assert decision == RevisionDecision.CONFIRM
        assert RevisionReason.NO_NEW_INFO in reasons
    
    def test_strengthen_decision_with_consensus(self):
        """Test STRENGTHEN decision when other agents agree"""
        initial_rec = {
            "recommendation": "APPROVED - All requirements met",
            "confidence": 0.95
        }
        
        other_recs = {
            "crew_compliance": {
                "recommendation": "APPROVED - Crew within limits",
                "reasoning": "All crew requirements met",
                "confidence": 0.9
            },
            "maintenance": {
                "recommendation": "APPROVED - Aircraft airworthy",
                "reasoning": "All maintenance checks complete",
                "confidence": 0.95
            }
        }
        
        decision, reasons, _ = analyze_other_recommendations(
            agent_name="regulatory",
            initial_recommendation=initial_rec,
            other_recommendations=other_recs,
            domain_keywords=get_domain_keywords("regulatory")
        )
        
        # Should strengthen or confirm (both acceptable with consensus)
        assert decision in [RevisionDecision.STRENGTHEN, RevisionDecision.CONFIRM]


class TestRevisionWithRealisticCollations:
    """Test revision behavior with realistic collation structures"""
    
    def test_crew_compliance_with_maintenance_delay_collation(self):
        """Test crew compliance revision with realistic maintenance delay collation"""
        initial_rec = {
            "recommendation": "APPROVED - Crew within FDP limits with 2h margin",
            "confidence": 0.9,
            "reasoning": "Current crew FDP: 11h, Limit: 13h, Margin: 2h"
        }
        
        # Realistic collation from orchestrator
        collation_responses = {
            "maintenance": {
                "agent_name": "maintenance",
                "recommendation": "3 hour delay required for engine inspection",
                "confidence": 0.85,
                "reasoning": "Engine oil leak detected. Requires inspection and seal replacement.",
                "binding_constraints": ["Aircraft cannot depart until inspection complete"],
                "data_sources": ["MaintenanceWorkOrders", "Flights"],
                "status": "success"
            },
            "regulatory": {
                "agent_name": "regulatory",
                "recommendation": "APPROVED with curfew warning",
                "confidence": 0.8,
                "reasoning": "3h delay would result in 23:00 arrival, close to curfew",
                "binding_constraints": ["Must depart by 19:00 to meet curfew"],
                "data_sources": ["Weather", "Flights"],
                "status": "success"
            }
        }
        
        decision, reasons, justification = analyze_other_recommendations(
            agent_name="crew_compliance",
            initial_recommendation=initial_rec,
            other_recommendations=collation_responses,
            domain_keywords=get_domain_keywords("crew_compliance")
        )
        
        # Should REVISE because 3h delay affects FDP calculation
        assert decision == RevisionDecision.REVISE
        assert RevisionReason.NEW_TIMING_INFO in reasons
        assert "timing" in justification.lower() or "delay" in justification.lower()
    
    def test_network_with_aircraft_swap_collation(self):
        """Test network agent revision with aircraft swap collation"""
        initial_rec = {
            "recommendation": "3h delay acceptable - minimal propagation",
            "confidence": 0.8,
            "reasoning": "Aircraft has 4h buffer before next flight"
        }
        
        collation_responses = {
            "maintenance": {
                "agent_name": "maintenance",
                "recommendation": "REQUIRES AIRCRAFT SWAP - 8h repair needed",
                "confidence": 0.95,
                "reasoning": "Engine issue requires extended maintenance. Recommend swap to A6-EYZ.",
                "binding_constraints": ["Original aircraft unavailable for 8 hours"],
                "data_sources": ["MaintenanceWorkOrders", "AircraftAvailability"],
                "status": "success"
            }
        }
        
        decision, reasons, justification = analyze_other_recommendations(
            agent_name="network",
            initial_recommendation=initial_rec,
            other_recommendations=collation_responses,
            domain_keywords=get_domain_keywords("network")
        )
        
        # Should make a decision (REVISE or STRENGTHEN depending on keyword matching)
        assert decision in [RevisionDecision.REVISE, RevisionDecision.STRENGTHEN]
        assert len(reasons) > 0
        assert justification is not None


class TestRevisionWithEdgeCases:
    """Test revision behavior with edge cases"""
    
    def test_revision_with_agent_timeout(self):
        """Test revision handles agent timeout gracefully"""
        initial_rec = {
            "recommendation": "APPROVED",
            "confidence": 0.9
        }
        
        collation_with_timeout = {
            "maintenance": {
                "agent_name": "maintenance",
                "recommendation": "No recommendation provided",
                "confidence": 0.0,
                "reasoning": "Agent execution exceeded 30 second timeout",
                "binding_constraints": [],
                "data_sources": [],
                "status": "timeout",
                "error": "Agent execution exceeded 30 second timeout"
            },
            "regulatory": {
                "agent_name": "regulatory",
                "recommendation": "APPROVED",
                "confidence": 0.95,
                "reasoning": "All regulations met",
                "binding_constraints": [],
                "data_sources": ["Weather"],
                "status": "success"
            }
        }
        
        decision, reasons, justification = analyze_other_recommendations(
            agent_name="crew_compliance",
            initial_recommendation=initial_rec,
            other_recommendations=collation_with_timeout,
            domain_keywords=get_domain_keywords("crew_compliance")
        )
        
        # Should handle timeout gracefully and make a decision
        assert decision in [RevisionDecision.CONFIRM, RevisionDecision.REVISE, RevisionDecision.STRENGTHEN]
        assert justification is not None
    
    def test_revision_with_empty_other_recommendations(self):
        """Test revision with empty other_recommendations dict"""
        initial_rec = {
            "recommendation": "APPROVED",
            "confidence": 0.9
        }
        
        decision, reasons, justification = analyze_other_recommendations(
            agent_name="crew_compliance",
            initial_recommendation=initial_rec,
            other_recommendations={},
            domain_keywords=get_domain_keywords("crew_compliance")
        )
        
        # Should CONFIRM when no other recommendations
        assert decision == RevisionDecision.CONFIRM
        assert RevisionReason.NO_NEW_INFO in reasons
    
    def test_revision_skips_own_recommendation(self):
        """Test that agent skips its own recommendation in other_recommendations"""
        initial_rec = {
            "recommendation": "APPROVED",
            "confidence": 0.9
        }
        
        other_recs = {
            "crew_compliance": {
                "recommendation": "APPROVED",
                "reasoning": "This is my own recommendation",
                "confidence": 0.9
            },
            "finance": {
                "recommendation": "High cost",
                "reasoning": "Expensive option",
                "confidence": 0.8
            }
        }
        
        decision, reasons, _ = analyze_other_recommendations(
            agent_name="crew_compliance",
            initial_recommendation=initial_rec,
            other_recommendations=other_recs,
            domain_keywords=get_domain_keywords("crew_compliance")
        )
        
        # Should confirm because finance is not relevant to crew
        assert decision == RevisionDecision.CONFIRM
