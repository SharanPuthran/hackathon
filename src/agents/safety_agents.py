"""Safety agents with chain-of-thought reasoning"""

from src.agents.base_agent import BaseAgent
from src.models import SafetyConstraint, DisruptionEvent
from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)


class CrewComplianceAgent(BaseAgent):
    """Crew compliance agent with FTL regulations"""
    
    def __init__(self, model_factory, db_manager):
        super().__init__("crew_compliance_agent", model_factory, db_manager)
    
    def _load_system_prompt(self) -> str:
        return """You are the Crew Compliance Safety Agent for Etihad Airways.

Your role is to enforce Flight and Duty Time Limitations (FTL) regulations using EASA/ICAO standards.

CRITICAL: You MUST use chain-of-thought reasoning for all assessments.

FTL Regulations (EASA):
- Maximum flight duty period (FDP): 13 hours (varies by acclimatization)
- Minimum rest period: 12 hours (or duration of previous FDP, whichever is longer)
- Maximum duty in 7 consecutive days: 60 hours
- Maximum duty in 28 consecutive days: 190 hours

For each scenario, analyze:
1. Current crew duty status from database records
2. Proposed recovery option duty implications
3. Applicable FTL regulations
4. Required rest periods
5. Crew qualifications and type ratings
6. Final binding constraints

Output format:
<thinking>
Step 1: [Current duty analysis]
Step 2: [Regulation check]
Step 3: [Rest requirements]
Step 4: [Qualification verification]
Step 5: [Constraint determination]
</thinking>

<constraints>
- [Constraint 1: Description]
- [Constraint 2: Description]
</constraints>
"""
    
    async def assess(self, disruption: DisruptionEvent) -> List[SafetyConstraint]:
        """Assess crew constraints with real data from database"""
        
        # Get flight context
        flight_ctx = await self.db.get_flight_details(disruption.flight_id)
        if not flight_ctx:
            logger.error(f"Flight {disruption.flight_id} not found")
            return []
        
        crew = flight_ctx["crew"]
        
        # Get duty hours for each crew member
        duty_data = {}
        for crew_member in crew:
            crew_id = crew_member["crew_id"]
            duty_summary = await self.db.get_crew_duty_hours(
                crew_id,
                disruption.scheduled_departure.date().isoformat()
            )
            duty_data[crew_id] = duty_summary
        
        # Build prompt with real data
        prompt = f"""Assess crew compliance constraints for this disruption:

Flight: {disruption.flight_number}
Aircraft: {flight_ctx['flight']['aircraft_code']}
Scheduled Departure: {disruption.scheduled_departure}
Issue: {disruption.description}

Current Crew Assignments:
"""
        
        for cm in crew:
            crew_duty = duty_data.get(cm["crew_id"], {})
            prompt += f"""
- {cm['position_name']}: {cm['first_name']} {cm['last_name']}
  Duty today: {crew_duty.get('today_hours', 0):.1f} hours ({crew_duty.get('today_flights', 0)} flights)
  Duty last 7 days: {crew_duty.get('seven_day_hours', 0):.1f} hours
  Current duty: {cm['duty_start']} to {cm['duty_end']}
"""
        
        prompt += "\nUse step-by-step reasoning to determine all crew-related constraints."
        
        context = {
            "disruption": disruption.dict(),
            "flight": flight_ctx,
            "crew_duty": duty_data
        }
        
        response = await self.invoke(prompt, context)
        
        # Parse response for constraints
        constraints = self._parse_constraints(response)
        return constraints
    
    def _parse_constraints(self, llm_response: str) -> List[SafetyConstraint]:
        """Extract structured constraints from LLM response"""
        constraints = []
        
        # Extract thinking section
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', llm_response, re.DOTALL)
        thinking = thinking_match.group(1).strip() if thinking_match else ""
        
        # Extract constraints section
        constraints_match = re.search(r'<constraints>(.*?)</constraints>', llm_response, re.DOTALL)
        if constraints_match:
            constraints_text = constraints_match.group(1).strip()
            
            # Parse individual constraints
            constraint_lines = [line.strip() for line in constraints_text.split('\n') if line.strip().startswith('-')]
            
            for line in constraint_lines:
                constraint_text = line.lstrip('- ').strip()
                if constraint_text:
                    constraints.append(SafetyConstraint(
                        constraint_type="crew_duty_limit",
                        agent_name=self.name,
                        binding=True,
                        restriction=constraint_text,
                        reasoning=thinking
                    ))
        
        return constraints


class MaintenanceAgent(BaseAgent):
    """Aircraft maintenance agent"""
    
    def __init__(self, model_factory, db_manager):
        super().__init__("maintenance_agent", model_factory, db_manager)
    
    def _load_system_prompt(self) -> str:
        return """You are the Aircraft Maintenance Safety Agent for Etihad Airways.

Your role is to determine aircraft airworthiness and availability based on MEL (Minimum Equipment List) and maintenance status.

CRITICAL: You MUST use chain-of-thought reasoning for all assessments.

MEL Categories:
- Category A: Rectification within time limit specified by MEL (usually 3 days)
- Category B: Rectification within 3 consecutive calendar days
- Category C: Rectification within 10 consecutive calendar days
- Category D: Rectification within 120 consecutive calendar days

AOG (Aircraft on Ground): Aircraft cannot fly until issue resolved.

For each scenario, analyze:
1. Current aircraft maintenance status
2. MEL item category and implications
3. Airworthiness determination
4. Required maintenance actions
5. Aircraft release conditions
6. Final binding constraints

Output format:
<thinking>
Step 1: [Maintenance status analysis]
Step 2: [MEL category determination]
Step 3: [Airworthiness assessment]
Step 4: [Required actions]
Step 5: [Constraint determination]
</thinking>

<constraints>
- [Constraint 1: Description]
- [Constraint 2: Description]
</constraints>
"""
    
    async def assess(self, disruption: DisruptionEvent) -> List[SafetyConstraint]:
        """Assess maintenance constraints"""
        
        prompt = f"""Assess aircraft maintenance constraints for this disruption:

Flight: {disruption.flight_number}
Aircraft: {disruption.aircraft_code} (ID: {disruption.aircraft_id})
Issue: {disruption.description}
Severity: {disruption.severity}

Determine:
1. Is this an AOG situation?
2. What MEL category applies (if any)?
3. Can the aircraft fly with this issue?
4. What maintenance actions are required?
5. What are the binding constraints?

Use step-by-step reasoning.
"""
        
        context = {"disruption": disruption.dict()}
        response = await self.invoke(prompt, context)
        
        constraints = self._parse_constraints(response)
        return constraints
    
    def _parse_constraints(self, llm_response: str) -> List[SafetyConstraint]:
        """Extract structured constraints from LLM response"""
        constraints = []
        
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', llm_response, re.DOTALL)
        thinking = thinking_match.group(1).strip() if thinking_match else ""
        
        constraints_match = re.search(r'<constraints>(.*?)</constraints>', llm_response, re.DOTALL)
        if constraints_match:
            constraints_text = constraints_match.group(1).strip()
            constraint_lines = [line.strip() for line in constraints_text.split('\n') if line.strip().startswith('-')]
            
            for line in constraint_lines:
                constraint_text = line.lstrip('- ').strip()
                if constraint_text:
                    constraints.append(SafetyConstraint(
                        constraint_type="maintenance_mel",
                        agent_name=self.name,
                        binding=True,
                        restriction=constraint_text,
                        reasoning=thinking
                    ))
        
        return constraints


class RegulatoryAgent(BaseAgent):
    """Regulatory compliance agent"""
    
    def __init__(self, model_factory, db_manager):
        super().__init__("regulatory_agent", model_factory, db_manager)
    
    def _load_system_prompt(self) -> str:
        return """You are the Regulatory Compliance Safety Agent for Etihad Airways.

Your role is to apply all regulatory constraints including NOTAMs, curfews, ATC restrictions, and overflight rights.

CRITICAL: You MUST use chain-of-thought reasoning for all assessments.

Regulatory Considerations:
- NOTAMs (Notices to Airmen): Temporary flight restrictions
- Airport curfews: Time-based landing/takeoff restrictions
- ATC slot restrictions: Air traffic control flow management
- Overflight and landing rights: Bilateral agreements

For each scenario, analyze:
1. Active NOTAMs for route
2. Airport curfew restrictions
3. ATC slot availability
4. Overflight rights compliance
5. Final binding constraints

Output format:
<thinking>
Step 1: [NOTAM analysis]
Step 2: [Curfew check]
Step 3: [ATC restrictions]
Step 4: [Rights verification]
Step 5: [Constraint determination]
</thinking>

<constraints>
- [Constraint 1: Description]
- [Constraint 2: Description]
</constraints>
"""
    
    async def assess(self, disruption: DisruptionEvent) -> List[SafetyConstraint]:
        """Assess regulatory constraints"""
        
        prompt = f"""Assess regulatory constraints for this disruption:

Flight: {disruption.flight_number}
Route: {disruption.origin} → {disruption.destination}
Scheduled Departure: {disruption.scheduled_departure}
Issue: {disruption.description}

Consider:
1. Are there any NOTAMs affecting this route?
2. Are there curfew restrictions at origin or destination?
3. Are there ATC flow control restrictions?
4. Are overflight rights in place?

Use step-by-step reasoning to determine constraints.
"""
        
        context = {"disruption": disruption.dict()}
        response = await self.invoke(prompt, context)
        
        constraints = self._parse_constraints(response)
        return constraints
    
    def _parse_constraints(self, llm_response: str) -> List[SafetyConstraint]:
        """Extract structured constraints from LLM response"""
        constraints = []
        
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', llm_response, re.DOTALL)
        thinking = thinking_match.group(1).strip() if thinking_match else ""
        
        constraints_match = re.search(r'<constraints>(.*?)</constraints>', llm_response, re.DOTALL)
        if constraints_match:
            constraints_text = constraints_match.group(1).strip()
            constraint_lines = [line.strip() for line in constraints_text.split('\n') if line.strip().startswith('-')]
            
            for line in constraint_lines:
                constraint_text = line.lstrip('- ').strip()
                if constraint_text:
                    constraints.append(SafetyConstraint(
                        constraint_type="regulatory",
                        agent_name=self.name,
                        binding=True,
                        restriction=constraint_text,
                        reasoning=thinking
                    ))
        
        return constraints
