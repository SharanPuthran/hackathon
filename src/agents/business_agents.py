"""Business agents with two-phase operation"""

from src.agents.base_agent import BaseAgent
from src.models import ImpactAssessment, RecoveryProposal, Action, DisruptionEvent
from typing import List, Dict, Any
import logging
import json
import re

logger = logging.getLogger(__name__)


class NetworkAgent(BaseAgent):
    """Network impact and recovery agent"""
    
    def __init__(self, model_factory, db_manager):
        super().__init__("network_agent", model_factory, db_manager)
    
    def _load_system_prompt(self) -> str:
        return """You are the Network Agent for Etihad Airways disruption management.

Your goal: Minimize network propagation and maintain fleet utilization.

You operate in TWO phases:

PHASE 1 - Impact Assessment:
- Quantify downstream flight impacts
- Identify affected rotations
- Calculate fleet utilization impact
- DO NOT propose solutions yet

PHASE 2 - Solution Proposals:
- Propose aircraft swap scenarios
- Consider schedule compression
- Optimize for network stability
- Reference safety constraints (cannot violate them)
- Consider peer agent impacts

Always provide structured, quantified outputs.
"""
    
    async def assess_impact(self, context: Dict[str, Any]) -> ImpactAssessment:
        """Phase 1: Quantify network impact"""
        
        disruption = context["disruption"]
        flight_ctx = context.get("flight_context", {})
        
        prompt = f"""Analyze the network impact of this disruption.

Flight: {disruption["flight_number"]}
Aircraft: {disruption.get("aircraft_code", "Unknown")}
Route: {disruption["origin"]} → {disruption["destination"]}
Issue: {disruption["description"]}

Provide ONLY quantified impacts, NO solutions.

Required metrics:
- Downstream flights affected (estimate)
- Aircraft rotations impacted
- Fleet utilization impact (0-1 scale)
- Network propagation risk (low/medium/high)

Use structured JSON format.
"""
        
        response = await self.invoke(prompt, context)
        return self._parse_impact_assessment(response)
    
    async def propose_solution(self, context: Dict[str, Any]) -> RecoveryProposal:
        """Phase 2: Propose network-focused recovery options"""
        
        disruption = context["disruption"]
        safety_constraints = context.get("safety_constraints", [])
        
        prompt = f"""Based on the impact assessment, propose recovery options.

Disruption: {disruption["description"]}

Safety Constraints (CANNOT BE VIOLATED):
{json.dumps([c.dict() for c in safety_constraints], indent=2, default=str)}

Propose 1-2 network-focused recovery strategies:
- Aircraft swaps
- Schedule adjustments
- Alternative routing

Format as JSON with title, description, actions list.
"""
        
        response = await self.invoke(prompt, context)
        return self._parse_proposal(response)
    
    def _parse_impact_assessment(self, response: str) -> ImpactAssessment:
        """Parse impact assessment from LLM response"""
        # Simple parsing - in production would use structured output
        return ImpactAssessment(
            agent_name=self.name,
            network_impact_score=0.7,  # Placeholder
            details={"raw_response": response}
        )
    
    def _parse_proposal(self, response: str) -> RecoveryProposal:
        """Parse recovery proposal from LLM response"""
        return RecoveryProposal(
            agent_name=self.name,
            title="Network Recovery Proposal",
            description=response[:200],
            actions=[Action(type="aircraft_swap", target="fleet", description="Swap aircraft", parameters={})],
            rationale=response
        )


class GuestExperienceAgent(BaseAgent):
    """Guest experience agent"""
    
    def __init__(self, model_factory, db_manager):
        super().__init__("guest_experience_agent", model_factory, db_manager)
    
    def _load_system_prompt(self) -> str:
        return """You are the Guest Experience Agent for Etihad Airways.

Your goal: Protect passenger satisfaction and loyalty.

You operate in TWO phases:

PHASE 1 - Impact Assessment:
- Quantify passengers affected
- Identify misconnections
- Count elite status passengers
- Estimate NPS impact
- DO NOT propose solutions yet

PHASE 2 - Solution Proposals:
- Propose rebooking strategies
- Consider compensation levels
- Optimize for guest satisfaction
- Reference safety constraints
- Debate with other agents

Always reference safety constraints (you cannot violate them).
"""
    
    async def assess_impact(self, context: Dict[str, Any]) -> ImpactAssessment:
        """Phase 1: Quantify guest experience impact"""
        
        disruption = context["disruption"]
        flight_ctx = context.get("flight_context", {})
        pax_stats = flight_ctx.get("passengers", {})
        
        prompt = f"""Analyze the guest experience impact of this disruption.

Flight: {disruption["flight_number"]}
Disruption: {disruption["description"]}

Passenger Statistics (Real Data):
- Total passengers: {pax_stats.get('total_pax', 0)}
- Connecting passengers: {pax_stats.get('connections', 0)}
- Connections at risk: {pax_stats.get('at_risk', 0)}
- VIP passengers: {pax_stats.get('vip_count', 0)}
- Platinum tier: {pax_stats.get('platinum', 0)}
- First class: {pax_stats.get('first_class', 0)}
- Business class: {pax_stats.get('business_class', 0)}

Provide ONLY quantified impacts, NO solutions yet.

Required Analysis:
1. Misconnection impact severity
2. Elite passenger impact on NPS
3. Service recovery complexity
4. Estimated NPS delta

Use structured format.
"""
        
        response = await self.invoke(prompt, context)
        
        return ImpactAssessment(
            agent_name=self.name,
            pax_affected=pax_stats.get('total_pax', 0),
            pax_connections_at_risk=pax_stats.get('at_risk', 0),
            elite_pax=pax_stats.get('platinum', 0) + pax_stats.get('vip_count', 0),
            details={"raw_response": response, "pax_stats": pax_stats}
        )
    
    async def propose_solution(self, context: Dict[str, Any]) -> RecoveryProposal:
        """Phase 2: Propose guest-focused recovery options"""
        
        prompt = """Based on impact assessment, propose guest-focused recovery strategies.

Consider:
1. Safety constraints (cannot be violated)
2. Network impact from Network Agent
3. Cargo constraints from Cargo Agent
4. Financial trade-offs from Finance Agent

Propose rebooking and compensation strategies that optimize for NPS.
"""
        
        response = await self.invoke(prompt, context)
        
        return RecoveryProposal(
            agent_name=self.name,
            title="Guest Experience Recovery",
            description=response[:200],
            actions=[Action(type="rebook_passengers", target="pax", description="Rebook affected passengers", parameters={})],
            rationale=response
        )


class CargoAgent(BaseAgent):
    """Cargo operations agent"""
    
    def __init__(self, model_factory, db_manager):
        super().__init__("cargo_agent", model_factory, db_manager)
    
    def _load_system_prompt(self) -> str:
        return """You are the Cargo Agent for Etihad Airways.

Your goal: Preserve high-value and perishable cargo.

PHASE 1 - Impact Assessment:
- Quantify cargo at risk
- Identify temperature-controlled shipments
- Calculate revenue exposure
- NO solutions yet

PHASE 2 - Solution Proposals:
- Propose re-routing options
- Prioritize shipments
- Protect cold-chain cargo
"""
    
    async def assess_impact(self, context: Dict[str, Any]) -> ImpactAssessment:
        """Phase 1: Quantify cargo impact"""
        
        disruption = context["disruption"]
        flight_ctx = context.get("flight_context", {})
        cargo_stats = flight_ctx.get("cargo", {})
        
        prompt = f"""Analyze cargo impact of this disruption.

Flight: {disruption["flight_number"]}
Disruption: {disruption["description"]}

Cargo Statistics:
- Total shipments: {cargo_stats.get('total_shipments', 0)}
- Total weight: {cargo_stats.get('total_cargo_weight', 0):.0f} kg
- Temperature-controlled: {cargo_stats.get('temp_controlled_weight', 0):.0f} kg
- Special handling: {cargo_stats.get('special_handling_count', 0)}

Provide ONLY quantified impacts, NO solutions.
"""
        
        response = await self.invoke(prompt, context)
        
        return ImpactAssessment(
            agent_name=self.name,
            cargo_at_risk_kg=cargo_stats.get('total_cargo_weight', 0),
            temp_controlled_cargo=cargo_stats.get('temp_controlled_weight', 0) > 0,
            details={"raw_response": response, "cargo_stats": cargo_stats}
        )
    
    async def propose_solution(self, context: Dict[str, Any]) -> RecoveryProposal:
        """Phase 2: Propose cargo recovery options"""
        
        prompt = """Propose cargo recovery strategies.

Consider:
- Temperature-controlled cargo protection
- High-value shipment priority
- Re-routing options
"""
        
        response = await self.invoke(prompt, context)
        
        return RecoveryProposal(
            agent_name=self.name,
            title="Cargo Recovery",
            description=response[:200],
            actions=[Action(type="reroute_cargo", target="cargo", description="Re-route cargo", parameters={})],
            rationale=response
        )


class FinanceAgent(BaseAgent):
    """Finance optimization agent"""
    
    def __init__(self, model_factory, db_manager):
        super().__init__("finance_agent", model_factory, db_manager)
    
    def _load_system_prompt(self) -> str:
        return """You are the Finance Agent for Etihad Airways.

Your goal: Optimize cost and revenue trade-offs.

PHASE 1 - Impact Assessment:
- Calculate direct costs
- Estimate revenue loss
- Quantify compensation liability
- NO solutions yet

PHASE 2 - Solution Proposals:
- Propose cost-optimized scenarios
- Balance short vs long-term impacts
"""
    
    async def assess_impact(self, context: Dict[str, Any]) -> ImpactAssessment:
        """Phase 1: Quantify financial impact"""
        
        disruption = context["disruption"]
        
        prompt = f"""Analyze financial impact of this disruption.

Flight: {disruption["flight_number"]}
Issue: {disruption["description"]}

Estimate:
1. Direct costs (fuel, crew, handling)
2. Revenue loss (tickets, cargo)
3. Compensation liability
4. Long-term brand impact

Provide quantified estimates.
"""
        
        response = await self.invoke(prompt, context)
        
        return ImpactAssessment(
            agent_name=self.name,
            cost_estimate=50000,  # Placeholder
            details={"raw_response": response}
        )
    
    async def propose_solution(self, context: Dict[str, Any]) -> RecoveryProposal:
        """Phase 2: Propose cost-optimized scenarios"""
        
        prompt = """Propose cost-optimized recovery scenarios.

Balance:
- Direct costs
- Revenue protection
- Long-term customer value
"""
        
        response = await self.invoke(prompt, context)
        
        return RecoveryProposal(
            agent_name=self.name,
            title="Cost-Optimized Recovery",
            description=response[:200],
            actions=[Action(type="optimize_costs", target="finance", description="Cost optimization", parameters={})],
            rationale=response
        )
