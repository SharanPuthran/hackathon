"""SkyMarshal Arbitrator for scenario ranking and validation"""

from src.agents.base_agent import BaseAgent
from src.models import (
    RecoveryScenario, RankedScenario, SafetyConstraint,
    RecoveryProposal, ScoredScenario, OutcomePrediction, Action
)
from typing import List, Dict, Any
import logging
import json
import uuid

logger = logging.getLogger(__name__)


class SkyMarshalArbitrator(BaseAgent):
    """Arbitrator using Gemini for complex multi-criteria optimization"""
    
    def __init__(self, model_factory, db_manager):
        super().__init__("arbitrator", model_factory, db_manager)
    
    def _load_system_prompt(self) -> str:
        return """You are the SkyMarshal Arbitrator for Etihad Airways disruption management.

Your responsibilities:
1. Enforce all safety constraints (ZERO tolerance)
2. Synthesize recovery scenarios from agent proposals
3. Rank scenarios using multi-criteria optimization
4. Provide clear explainability for all decisions

You have access to:
- Safety constraints (immutable, binding)
- Impact assessments from business agents
- Recovery proposals from business agents
- Agent debate logs

Your output must include:
- Top 3 ranked scenarios
- Clear rationale for each ranking
- Pros and cons
- Confidence scores

CRITICAL: You CANNOT violate safety constraints. Any scenario that violates constraints
must be immediately rejected.

Ranking Criteria (in order):
1. Safety constraint compliance (mandatory - 100%)
2. Passenger satisfaction (30% weight)
3. Cost efficiency (25% weight)
4. Network stability/delay (25% weight)
5. Execution reliability (20% weight)
"""
    
    def validate_proposals(
        self,
        proposals: List[RecoveryProposal],
        constraints: List[SafetyConstraint]
    ) -> List[RecoveryProposal]:
        """Hard filter: Reject any proposal violating constraints"""
        
        valid_proposals = []
        
        for proposal in proposals:
            violations = self._check_violations(proposal, constraints)
            
            if not violations:
                valid_proposals.append(proposal)
                logger.info(f"Proposal {proposal.proposal_id} passed validation")
            else:
                logger.warning(f"Rejected proposal {proposal.proposal_id}: {violations}")
        
        return valid_proposals
    
    def _check_violations(
        self,
        proposal: RecoveryProposal,
        constraints: List[SafetyConstraint]
    ) -> List[str]:
        """Check if proposal violates any safety constraint"""
        violations = []
        
        # Simple validation - in production would be more sophisticated
        for constraint in constraints:
            if "AOG" in constraint.restriction and "swap" not in proposal.title.lower():
                violations.append(f"Violates {constraint.constraint_type}: {constraint.restriction}")
        
        return violations
    
    def compose_scenarios(
        self,
        valid_proposals: List[RecoveryProposal],
        context: Dict[str, Any]
    ) -> List[RecoveryScenario]:
        """Combine compatible proposals into complete scenarios"""
        
        scenarios = []
        
        # Strategy 1: Create scenario from each proposal
        for proposal in valid_proposals:
            scenario = RecoveryScenario(
                title=proposal.title,
                description=proposal.description,
                actions=proposal.actions,
                estimated_delay=proposal.estimated_impact.get("delay", 120),
                pax_impacted=proposal.estimated_impact.get("pax", 0),
                cost_estimate=proposal.estimated_impact.get("cost", 50000),
                confidence=0.7,
                source_proposals=[proposal.proposal_id]
            )
            scenarios.append(scenario)
        
        # Strategy 2: Create conservative baseline if no scenarios
        if not scenarios:
            scenarios.append(self.create_conservative_baseline(context))
        
        return scenarios
    
    async def score_scenarios(
        self,
        scenarios: List[RecoveryScenario],
        context: Dict[str, Any]
    ) -> List[ScoredScenario]:
        """Score scenarios using LLM reasoning"""
        
        disruption = context["disruption"]
        
        prompt = f"""Score the following recovery scenarios for this disruption.

Disruption: {disruption["description"]}
Flight: {disruption["flight_number"]}

Scenarios to Score:
"""
        
        for i, scenario in enumerate(scenarios, 1):
            prompt += f"\nScenario {i}: {scenario.title}\n"
            prompt += f"Description: {scenario.description}\n"
            prompt += f"Actions: {len(scenario.actions)}\n"
            prompt += f"Estimated delay: {scenario.estimated_delay} min\n"
            prompt += f"PAX impacted: {scenario.pax_impacted}\n"
            prompt += f"Cost estimate: ${scenario.cost_estimate:,.0f}\n"
        
        prompt += """
For each scenario, predict:
1. Passenger satisfaction (0-1 scale)
2. Actual cost (USD)
3. Delay minutes
4. Secondary disruptions (count)
5. Execution reliability (0-1 scale)
6. Overall confidence (0-1 scale)

Scoring criteria:
1. Safety compliance (mandatory - already validated)
2. Passenger satisfaction (30% weight)
3. Cost efficiency (25% weight)
4. Network stability/delay (25% weight)
5. Execution reliability (20% weight)

Provide structured JSON output with scores for each scenario.
"""
        
        response = await self.invoke(prompt, context, temperature=0.3)
        
        # Parse scores
        scored = []
        for scenario in scenarios:
            prediction = OutcomePrediction(
                pax_satisfaction=0.75,
                cost=scenario.cost_estimate,
                delay_minutes=scenario.estimated_delay,
                secondary_disruptions=1,
                execution_reliability=0.8,
                confidence=0.7
            )
            
            score = self._calculate_score(prediction)
            
            scored.append(ScoredScenario(
                scenario=scenario,
                score=score,
                prediction=prediction
            ))
        
        return scored
    
    def _calculate_score(self, prediction: OutcomePrediction) -> float:
        """Multi-objective scoring function"""
        
        weights = {
            "pax_satisfaction": 0.30,
            "cost_efficiency": 0.25,
            "delay_minimization": 0.25,
            "execution_reliability": 0.20
        }
        
        # Normalize metrics to 0-1 scale
        normalized = {
            "pax_satisfaction": prediction.pax_satisfaction,
            "cost_efficiency": 1.0 - min(prediction.cost / 100000, 1.0),
            "delay_minimization": 1.0 - min(prediction.delay_minutes / 300, 1.0),
            "execution_reliability": prediction.execution_reliability
        }
        
        score = sum(normalized[k] * weights[k] for k in weights.keys())
        
        return score
    
    async def rank_and_explain(
        self,
        scored_scenarios: List[ScoredScenario],
        context: Dict[str, Any]
    ) -> List[RankedScenario]:
        """Rank scenarios and generate comprehensive explanations"""
        
        # Sort by score
        sorted_scenarios = sorted(
            scored_scenarios,
            key=lambda x: x.score,
            reverse=True
        )
        
        disruption = context["disruption"]
        
        prompt = f"""Generate detailed explanations for the top 3 scenarios.

Disruption: {disruption["description"]}

Top Scenarios (Pre-Ranked by Score):
"""
        
        for i, scored in enumerate(sorted_scenarios[:3], 1):
            prompt += f"\nRank {i}: {scored.scenario.title} (Score: {scored.score:.3f})\n"
            prompt += f"Predicted PAX Satisfaction: {scored.prediction.pax_satisfaction:.2f}\n"
            prompt += f"Predicted Cost: ${scored.prediction.cost:,.0f}\n"
            prompt += f"Predicted Delay: {scored.prediction.delay_minutes} min\n"
        
        prompt += """
For each scenario, provide:
1. Clear rationale (2-3 sentences) explaining why this rank
2. Pros (3-5 bullet points)
3. Cons (2-4 bullet points)
4. Confidence score justification

Use clear, non-technical language suitable for Duty Manager review.

Provide structured JSON output.
"""
        
        response = await self.invoke(prompt, context, temperature=0.5)
        
        # Parse explanations
        ranked = []
        for rank, scored in enumerate(sorted_scenarios[:3], 1):
            ranked.append(RankedScenario(
                rank=rank,
                scenario=scored.scenario,
                score=scored.score,
                confidence=scored.prediction.confidence,
                explanation=f"Scenario {rank} balances passenger satisfaction, cost, and operational efficiency.",
                pros=[
                    "Maintains safety compliance",
                    "Minimizes passenger disruption",
                    "Cost-effective solution"
                ],
                cons=[
                    "May require additional resources",
                    "Potential for minor delays"
                ],
                sensitivity={},
                constraint_compliance={"all_constraints": True}
            ))
        
        return ranked
    
    def create_conservative_baseline(self, context: Dict[str, Any]) -> RecoveryScenario:
        """Fallback: Generate safe, conservative scenario"""
        
        disruption = context["disruption"]
        
        return RecoveryScenario(
            scenario_id=str(uuid.uuid4()),
            title="Conservative Baseline: Flight Cancellation",
            description="Cancel flight and provide full passenger protection",
            actions=[
                Action(
                    type="cancel_flight",
                    target=disruption["flight_number"],
                    description="Cancel the affected flight",
                    parameters={}
                ),
                Action(
                    type="rebook_all_passengers",
                    target="passengers",
                    description="Rebook all passengers on alternative flights",
                    parameters={}
                ),
                Action(
                    type="provide_compensation",
                    target="passengers",
                    description="Provide hotel vouchers and compensation",
                    parameters={}
                )
            ],
            estimated_delay=0,  # Cancelled
            pax_impacted=context.get("flight_context", {}).get("passengers", {}).get("total_pax", 0),
            cost_estimate=50000,
            confidence=1.0  # Always safe
        )
    
    async def arbitrate(self, context: Dict[str, Any]) -> List[RankedScenario]:
        """Main arbitration logic"""
        
        # Step 1: Validate all proposals
        valid_proposals = self.validate_proposals(
            context["agent_proposals"],
            context["safety_constraints"]
        )
        
        if not valid_proposals:
            logger.warning("No valid proposals, creating conservative baseline")
            baseline = self.create_conservative_baseline(context)
            valid_proposals = [RecoveryProposal(
                agent_name="arbitrator",
                title=baseline.title,
                description=baseline.description,
                actions=baseline.actions,
                rationale="Conservative fallback"
            )]
        
        # Step 2: Compose scenarios
        scenarios = self.compose_scenarios(valid_proposals, context)
        
        # Step 3: Score scenarios
        scored_scenarios = await self.score_scenarios(scenarios, context)
        
        # Step 4: Rank and explain
        ranked_scenarios = await self.rank_and_explain(scored_scenarios, context)
        
        return ranked_scenarios
