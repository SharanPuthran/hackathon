"""LangGraph orchestrator for SkyMarshal workflow"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any, List
import logging
import asyncio
from datetime import datetime

from src.models import SkyMarshalState, DisruptionEvent
from src.agents import (
    CrewComplianceAgent, MaintenanceAgent, RegulatoryAgent,
    NetworkAgent, GuestExperienceAgent, CargoAgent, FinanceAgent,
    SkyMarshalArbitrator
)
from src.config import SAFETY_TIMEOUT_SECONDS, MAX_DEBATE_ROUNDS

logger = logging.getLogger(__name__)


class SkyMarshalOrchestrator:
    """Orchestrates the complete SkyMarshal workflow"""
    
    def __init__(self, model_factory, db_manager):
        self.model_factory = model_factory
        self.db = db_manager
        
        # Initialize agents
        self.safety_agents = [
            CrewComplianceAgent(model_factory, db_manager),
            MaintenanceAgent(model_factory, db_manager),
            RegulatoryAgent(model_factory, db_manager)
        ]
        
        self.business_agents = [
            NetworkAgent(model_factory, db_manager),
            GuestExperienceAgent(model_factory, db_manager),
            CargoAgent(model_factory, db_manager),
            FinanceAgent(model_factory, db_manager)
        ]
        
        self.arbitrator = SkyMarshalArbitrator(model_factory, db_manager)
        
        # Create workflow
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create LangGraph state machine"""
        
        workflow = StateGraph(dict)
        
        # Define nodes
        workflow.add_node("trigger", self.handle_trigger)
        workflow.add_node("safety_assessment", self.run_safety_assessment)
        workflow.add_node("guardrail_check", self.check_guardrails)
        workflow.add_node("impact_assessment", self.run_impact_assessment)
        workflow.add_node("option_formulation", self.run_option_formulation)
        workflow.add_node("arbitration", self.run_arbitration)
        workflow.add_node("human_approval", self.wait_for_human_approval)
        workflow.add_node("execution", self.run_execution)
        workflow.add_node("escalate", self.handle_escalation)
        
        # Define edges
        workflow.set_entry_point("trigger")
        workflow.add_edge("trigger", "safety_assessment")
        workflow.add_edge("safety_assessment", "guardrail_check")
        
        workflow.add_conditional_edges(
            "guardrail_check",
            self.route_after_guardrail_check,
            {
                "proceed": "impact_assessment",
                "escalate": "escalate"
            }
        )
        
        workflow.add_edge("impact_assessment", "option_formulation")
        workflow.add_edge("option_formulation", "arbitration")
        workflow.add_edge("arbitration", "human_approval")
        workflow.add_edge("human_approval", "execution")
        workflow.add_edge("execution", END)
        workflow.add_edge("escalate", END)
        
        return workflow.compile()
    
    async def handle_trigger(self, state: Dict) -> Dict:
        """Phase 1: Initialize disruption"""
        logger.info(f"=== PHASE 1: TRIGGER ===")
        
        disruption = state["disruption"]
        logger.info(f"Disruption: {disruption['flight_number']} - {disruption['description']}")
        
        # Load flight context from database
        flight_ctx = await self.db.get_flight_details(disruption["flight_id"])
        
        state["current_phase"] = "trigger"
        state["phase_history"] = ["trigger"]
        state["flight_context"] = flight_ctx
        state["timestamp"] = datetime.now().isoformat()
        
        return state
    
    async def run_safety_assessment(self, state: Dict) -> Dict:
        """Phase 2: Safety assessment with mandatory completion"""
        logger.info(f"=== PHASE 2: SAFETY ASSESSMENT ===")
        
        disruption_event = DisruptionEvent(**state["disruption"])
        
        # Run all safety agents in parallel with timeout
        tasks = [
            asyncio.wait_for(
                agent.assess(disruption_event),
                timeout=SAFETY_TIMEOUT_SECONDS
            )
            for agent in self.safety_agents
        ]
        
        constraints = []
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Safety agent {i} failed: {result}")
                    state["guardrail_triggered"] = True
                    state["guardrail_triggers"] = state.get("guardrail_triggers", []) + ["safety_agent_timeout"]
                else:
                    constraints.extend(result)
            
            state["safety_constraints"] = [c.dict() for c in constraints]
            state["current_phase"] = "safety_assessment"
            logger.info(f"Safety constraints identified: {len(constraints)}")
            
        except Exception as e:
            logger.critical(f"Safety assessment failed: {e}")
            state["guardrail_triggered"] = True
            state["escalation_required"] = True
            state["guardrail_triggers"] = state.get("guardrail_triggers", []) + ["safety_assessment_failure"]
        
        return state
    
    async def check_guardrails(self, state: Dict) -> Dict:
        """Guardrail checkpoint"""
        logger.info(f"=== GUARDRAIL CHECK ===")
        
        if state.get("guardrail_triggered"):
            logger.error("Guardrail triggered - escalating to human")
            state["escalation_required"] = True
        
        return state
    
    def route_after_guardrail_check(self, state: Dict) -> str:
        """Route after guardrail check"""
        if state.get("escalation_required"):
            return "escalate"
        return "proceed"
    
    async def run_impact_assessment(self, state: Dict) -> Dict:
        """Phase 3: Impact assessment"""
        logger.info(f"=== PHASE 3: IMPACT ASSESSMENT ===")
        
        context = {
            "disruption": state["disruption"],
            "flight_context": state.get("flight_context", {}),
            "safety_constraints": state.get("safety_constraints", [])
        }
        
        # Run impact assessments in parallel
        tasks = [agent.assess_impact(context) for agent in self.business_agents]
        results = await asyncio.gather(*tasks)
        
        impact_assessments = {}
        for agent, assessment in zip(self.business_agents, results):
            impact_assessments[agent.name] = assessment.dict()
        
        state["impact_assessments"] = impact_assessments
        state["current_phase"] = "impact_assessment"
        logger.info(f"Impact assessments completed: {len(impact_assessments)}")
        
        return state
    
    async def run_option_formulation(self, state: Dict) -> Dict:
        """Phase 4: Option formulation"""
        logger.info(f"=== PHASE 4: OPTION FORMULATION ===")
        
        context = {
            "disruption": state["disruption"],
            "flight_context": state.get("flight_context", {}),
            "safety_constraints": state.get("safety_constraints", []),
            "impact_assessments": state.get("impact_assessments", {})
        }
        
        # Business agents propose solutions
        tasks = [agent.propose_solution(context) for agent in self.business_agents]
        proposals = await asyncio.gather(*tasks)
        
        state["agent_proposals"] = [p.dict() for p in proposals]
        state["current_phase"] = "option_formulation"
        logger.info(f"Proposals generated: {len(proposals)}")
        
        return state
    
    async def run_arbitration(self, state: Dict) -> Dict:
        """Phase 5: Arbitration"""
        logger.info(f"=== PHASE 5: ARBITRATION ===")
        
        from src.models import SafetyConstraint, RecoveryProposal
        
        context = {
            "disruption": state["disruption"],
            "flight_context": state.get("flight_context", {}),
            "safety_constraints": [SafetyConstraint(**c) for c in state.get("safety_constraints", [])],
            "impact_assessments": state.get("impact_assessments", {}),
            "agent_proposals": [RecoveryProposal(**p) for p in state.get("agent_proposals", [])]
        }
        
        # Arbitrator ranks scenarios
        ranked_scenarios = await self.arbitrator.arbitrate(context)
        
        state["ranked_scenarios"] = [rs.dict() for rs in ranked_scenarios]
        state["current_phase"] = "arbitration"
        logger.info(f"Scenarios ranked: {len(ranked_scenarios)}")
        
        return state
    
    async def wait_for_human_approval(self, state: Dict) -> Dict:
        """Phase 6: Human approval (placeholder)"""
        logger.info(f"=== PHASE 6: HUMAN APPROVAL ===")
        
        # In real implementation, this would wait for human input
        # For demo, auto-approve top scenario
        ranked_scenarios = state.get("ranked_scenarios", [])
        if ranked_scenarios:
            state["human_decision"] = {
                "chosen_scenario_id": ranked_scenarios[0]["scenario"]["scenario_id"],
                "was_override": False,
                "override_reason": None,
                "timestamp": datetime.now().isoformat(),
                "decision_maker": "Demo User"
            }
        
        state["current_phase"] = "human_approval"
        logger.info("Human approval received (auto-approved for demo)")
        
        return state
    
    async def run_execution(self, state: Dict) -> Dict:
        """Phase 7: Execution (simulated)"""
        logger.info(f"=== PHASE 7: EXECUTION ===")
        
        # Simulate execution
        chosen_scenario = None
        for scenario in state.get("ranked_scenarios", []):
            if scenario["scenario"]["scenario_id"] == state["human_decision"]["chosen_scenario_id"]:
                chosen_scenario = scenario["scenario"]
                break
        
        if chosen_scenario:
            logger.info(f"Executing scenario: {chosen_scenario['title']}")
            logger.info(f"Actions: {len(chosen_scenario['actions'])}")
            
            # Simulate action execution
            for action in chosen_scenario["actions"]:
                logger.info(f"  - {action['type']}: {action['description']}")
                await asyncio.sleep(0.5)  # Simulate execution time
        
        state["current_phase"] = "execution"
        state["execution_complete"] = True
        
        return state
    
    async def handle_escalation(self, state: Dict) -> Dict:
        """Handle escalation"""
        logger.error(f"=== ESCALATION ===")
        logger.error(f"Triggers: {state.get('guardrail_triggers', [])}")
        
        state["current_phase"] = "escalated"
        
        return state
    
    async def run(self, disruption: DisruptionEvent) -> Dict:
        """Run complete workflow"""
        logger.info(f"Starting SkyMarshal workflow for {disruption.flight_number}")
        
        initial_state = {
            "disruption": disruption.dict(),
            "current_phase": "trigger",
            "phase_history": [],
            "safety_constraints": [],
            "impact_assessments": {},
            "agent_proposals": [],
            "debate_log": [],
            "ranked_scenarios": [],
            "human_decision": None,
            "guardrail_triggered": False,
            "escalation_required": False,
            "guardrail_triggers": []
        }
        
        result = await self.workflow.ainvoke(initial_state)
        
        logger.info(f"Workflow completed: {result['current_phase']}")
        
        return result
