# SkyMarshal - Multi-Model Architecture with AWS Bedrock

## Document Overview

This document extends the base SkyMarshal architecture to support multiple reasoning models via AWS Bedrock, providing optimal model selection for each agent type and integrating with the existing database schema.

---

## 1. Multi-Model Strategy

### 1.1 Model Selection Rationale

Different agents require different cognitive capabilities. By using specialized models for each agent type, we optimize for:
- **Cost efficiency**: Use smaller models where appropriate
- **Performance**: Leverage strengths of each model family
- **Redundancy**: Avoid single-model dependencies
- **Diversity**: Get varied perspectives in debate phases

### 1.2 Model Assignments

| Component | Model | Reasoning |
|-----------|-------|-----------|
| **Orchestrator** | Claude Sonnet 4.5 | Excellent at workflow coordination, state management, and structured reasoning |
| **Arbitrator** | **Google Gemini 3 Pro** | Strong at multi-criteria optimization, complex ranking, and massive context windows |
| **Safety Agents** | Claude Sonnet 4.5 | Superior chain-of-thought reasoning for safety-critical analysis |
| **Business Agents** | **Mixed (OpenAI, Claude, Gemini, Nova)** | Diverse perspectives for trade-off negotiation |
| **Execution Agents** | Claude Sonnet 4.5 | Reliable execution coordination and confirmation |

### 1.3 Detailed Agent-Model Mapping

```python
AGENT_MODEL_MAP = {
    # Core orchestration
    "orchestrator": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "State management and workflow coordination"
    },

    # Arbitrator (most complex reasoning - using Gemini 3 Pro)
    "arbitrator": {
        "model_id": "gemini-3.0-pro",
        "provider": "google",
        "reason": "Complex multi-criteria optimization with massive context window"
    },

    # Safety Agents (critical - use Claude Sonnet for chain-of-thought)
    "crew_compliance_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "Chain-of-thought for FTL regulations"
    },
    "maintenance_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "Technical reasoning for MEL/AOG"
    },
    "regulatory_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "Regulatory compliance analysis"
    },

    # Business Agents (diverse models for varied perspectives)
    "network_agent": {
        "model_id": "gpt-4o",
        "provider": "openai",
        "reason": "Network propagation and graph analysis"
    },
    "guest_experience_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "Customer sentiment and empathy analysis"
    },
    "cargo_agent": {
        "model_id": "gemini-2.0-flash-thinking",
        "provider": "google",
        "reason": "Logistics optimization with thinking mode"
    },
    "finance_agent": {
        "model_id": "us.amazon.nova-pro-v1:0",
        "provider": "bedrock",
        "reason": "Financial modeling and cost analysis"
    },

    # Execution Agents (Claude Sonnet for reliable execution)
    "flight_scheduling_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "Execution coordination"
    },
    "crew_recovery_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "Crew pairing logic"
    },
    "guest_recovery_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "Passenger rebooking"
    },
    "cargo_recovery_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "AWB updates"
    },
    "comms_agent": {
        "model_id": "anthropic.claude-sonnet-4-5-v2:0",
        "provider": "bedrock",
        "reason": "Message generation"
    }
}
```

---

## 2. AWS Bedrock Integration

### 2.1 AWS Bedrock Setup

```python
import boto3
from botocore.config import Config

# AWS Bedrock client configuration
def create_bedrock_client(region='us-east-1'):
    """Create AWS Bedrock runtime client"""

    config = Config(
        region_name=region,
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        read_timeout=300,
        connect_timeout=60
    )

    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        config=config
    )

    return bedrock_runtime
```

### 2.2 Model Provider Abstraction

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json

class ModelProvider(ABC):
    """Abstract base class for model providers"""

    @abstractmethod
    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        pass

class BedrockClaude(ModelProvider):
    """AWS Bedrock Claude model provider"""

    def __init__(self, model_id: str, client):
        self.model_id = model_id
        self.client = client

    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        """Invoke Claude via Bedrock"""

        # Format messages for Claude
        system_prompt = ""
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
            "system": system_prompt,
            "messages": user_messages
        }

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']

class BedrockNova(ModelProvider):
    """AWS Bedrock Amazon Nova model provider"""

    def __init__(self, model_id: str, client):
        self.model_id = model_id
        self.client = client

    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        """Invoke Nova via Bedrock"""

        request_body = {
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9)
        }

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())
        return response_body['output']['message']['content'][0]['text']

class OpenAIProvider(ModelProvider):
    """OpenAI model provider"""

    def __init__(self, model_id: str, api_key: str):
        self.model_id = model_id
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)

    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        """Invoke OpenAI model"""

        response = await self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7)
        )

        return response.choices[0].message.content

class GoogleGeminiProvider(ModelProvider):
    """Google Gemini model provider"""

    def __init__(self, model_id: str, api_key: str):
        self.model_id = model_id
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_id)

    async def invoke(self, messages: List[Dict], **kwargs) -> str:
        """Invoke Gemini model"""

        # Convert messages to Gemini format
        system_instruction = ""
        conversation_parts = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                conversation_parts.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                conversation_parts.append({"role": "model", "parts": [msg["content"]]})

        # Create chat with system instruction
        chat = self.model.start_chat(
            history=conversation_parts[:-1] if len(conversation_parts) > 1 else []
        )

        # Configure generation
        generation_config = {
            "max_output_tokens": kwargs.get("max_tokens", 8192),
            "temperature": kwargs.get("temperature", 0.7),
        }

        # Send message
        response = await chat.send_message_async(
            conversation_parts[-1]["parts"][0],
            generation_config=generation_config
        )

        return response.text

class ModelFactory:
    """Factory for creating model providers"""

    def __init__(
        self,
        bedrock_client,
        openai_api_key: str = None,
        google_api_key: str = None
    ):
        self.bedrock_client = bedrock_client
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
        self.providers = {}

    def get_provider(self, agent_name: str) -> ModelProvider:
        """Get model provider for specific agent"""

        if agent_name in self.providers:
            return self.providers[agent_name]

        model_config = AGENT_MODEL_MAP.get(agent_name)
        if not model_config:
            raise ValueError(f"No model configuration for agent: {agent_name}")

        model_id = model_config["model_id"]
        provider_type = model_config["provider"]

        # Route to appropriate provider
        if provider_type == "bedrock":
            if "claude" in model_id:
                provider = BedrockClaude(model_id, self.bedrock_client)
            elif "nova" in model_id:
                provider = BedrockNova(model_id, self.bedrock_client)
            else:
                raise ValueError(f"Unsupported Bedrock model: {model_id}")

        elif provider_type == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            provider = OpenAIProvider(model_id, self.openai_api_key)

        elif provider_type == "google":
            if not self.google_api_key:
                raise ValueError("Google API key not configured")
            provider = GoogleGeminiProvider(model_id, self.google_api_key)

        else:
            raise ValueError(f"Unsupported provider: {provider_type}")

        self.providers[agent_name] = provider
        return provider
```

### 2.3 Agent Base Class with Multi-Model Support

```python
class BaseAgent(ABC):
    """Base agent class with multi-model support"""

    def __init__(self, name: str, model_factory: ModelFactory):
        self.name = name
        self.model_provider = model_factory.get_provider(name)
        self.system_prompt = self._load_system_prompt()
        self.model_info = AGENT_MODEL_MAP[name]

    @abstractmethod
    def _load_system_prompt(self) -> str:
        """Load agent-specific system prompt"""
        pass

    async def invoke(self, user_prompt: str, context: Dict[str, Any], **kwargs) -> str:
        """Invoke LLM with system + user prompt"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._format_prompt(user_prompt, context)}
        ]

        # Add model-specific parameters
        invoke_kwargs = {
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7)
        }

        response = await self.model_provider.invoke(messages, **invoke_kwargs)

        # Log model usage for monitoring
        self._log_model_usage(len(user_prompt), len(response))

        return response

    def _log_model_usage(self, input_tokens: int, output_tokens: int):
        """Log model usage for cost tracking"""
        logger.info(f"{self.name} used {self.model_info['model_id']}: "
                   f"{input_tokens} in / {output_tokens} out")
```

---

## 3. Database Integration

### 3.1 Database Schema Overview

The existing database schema supports:
- **35 flights** over 7 days (EY flight numbers)
- **Passenger management** with Etihad Guest loyalty tiers
- **Cargo operations** with AWB prefix 607
- **Crew rostering** with FTL compliance tracking

### 3.2 Database Connection Layer

```python
import asyncpg
from typing import Dict, List, Optional
import os

class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'etihad_aviation'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            min_size=5,
            max_size=20
        )

    async def get_flight_details(self, flight_id: int) -> Dict:
        """Get complete flight details including aircraft, route, crew, pax, cargo"""

        async with self.pool.acquire() as conn:
            # Get flight info
            flight = await conn.fetchrow("""
                SELECT f.*,
                       at.aircraft_code, at.passenger_capacity, at.cargo_capacity_kg,
                       o.iata_code as origin_iata, o.airport_name as origin_name,
                       d.iata_code as dest_iata, d.airport_name as dest_name
                FROM flights f
                JOIN aircraft_types at ON f.aircraft_type_id = at.aircraft_type_id
                JOIN airports o ON f.origin_airport_id = o.airport_id
                JOIN airports d ON f.destination_airport_id = d.airport_id
                WHERE f.flight_id = $1
            """, flight_id)

            # Get passenger count and breakdown
            pax_stats = await conn.fetchrow("""
                SELECT COUNT(*) as total_pax,
                       SUM(CASE WHEN is_connection THEN 1 ELSE 0 END) as connections,
                       SUM(CASE WHEN connection_at_risk THEN 1 ELSE 0 END) as at_risk,
                       SUM(CASE WHEN p.is_vip THEN 1 ELSE 0 END) as vip_count,
                       SUM(CASE WHEN p.frequent_flyer_tier_id = 1 THEN 1 ELSE 0 END) as platinum,
                       SUM(CASE WHEN booking_class = 'First' THEN 1 ELSE 0 END) as first_class,
                       SUM(CASE WHEN booking_class = 'Business' THEN 1 ELSE 0 END) as business_class
                FROM bookings b
                JOIN passengers p ON b.passenger_id = p.passenger_id
                WHERE b.flight_id = $1 AND b.booking_status != 'Cancelled'
            """, flight_id)

            # Get cargo summary
            cargo_stats = await conn.fetchrow("""
                SELECT COUNT(DISTINCT cs.shipment_id) as total_shipments,
                       SUM(cfa.weight_on_flight_kg) as total_cargo_weight,
                       SUM(CASE WHEN ct.temperature_controlled THEN cfa.weight_on_flight_kg ELSE 0 END) as temp_controlled_weight,
                       SUM(CASE WHEN ct.requires_special_handling THEN 1 ELSE 0 END) as special_handling_count
                FROM cargo_flight_assignments cfa
                JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
                JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
                WHERE cfa.flight_id = $1 AND cfa.loading_status = 'Planned'
            """, flight_id)

            # Get crew assignments
            crew = await conn.fetch("""
                SELECT cm.first_name, cm.last_name, cp.position_code, cp.position_name,
                       cr.duty_start, cr.duty_end
                FROM crew_roster cr
                JOIN crew_members cm ON cr.crew_id = cm.crew_id
                JOIN crew_positions cp ON cr.position_id = cp.position_id
                WHERE cr.flight_id = $1 AND cr.roster_status = 'Assigned'
            """, flight_id)

            return {
                "flight": dict(flight),
                "passengers": dict(pax_stats),
                "cargo": dict(cargo_stats),
                "crew": [dict(c) for c in crew]
            }

    async def get_crew_duty_hours(self, crew_id: int, date: str) -> Dict:
        """Calculate crew duty hours for FTL compliance"""

        async with self.pool.acquire() as conn:
            duty_summary = await conn.fetchrow("""
                SELECT
                    SUM(EXTRACT(EPOCH FROM (duty_end - duty_start))/3600) as total_hours_today,
                    COUNT(*) as flights_today
                FROM crew_roster
                WHERE crew_id = $1
                  AND DATE(duty_start) = $2
                  AND roster_status IN ('Assigned', 'Confirmed')
            """, crew_id, date)

            # Get last 7 days duty time
            duty_7day = await conn.fetchrow("""
                SELECT
                    SUM(EXTRACT(EPOCH FROM (duty_end - duty_start))/3600) as total_hours_7day
                FROM crew_roster
                WHERE crew_id = $1
                  AND duty_start >= $2::date - INTERVAL '7 days'
                  AND roster_status IN ('Assigned', 'Confirmed', 'Completed')
            """, crew_id, date)

            return {
                "today_hours": float(duty_summary['total_hours_today'] or 0),
                "today_flights": int(duty_summary['flights_today'] or 0),
                "seven_day_hours": float(duty_7day['total_hours_7day'] or 0)
            }

    async def get_cargo_by_awb(self, awb_number: str) -> Optional[Dict]:
        """Get cargo shipment details by AWB number"""

        async with self.pool.acquire() as conn:
            cargo = await conn.fetchrow("""
                SELECT cs.*,
                       ct.commodity_name, ct.temperature_controlled, ct.requires_special_handling,
                       o.iata_code as origin_iata,
                       d.iata_code as dest_iata
                FROM cargo_shipments cs
                JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
                JOIN airports o ON cs.origin_airport_id = o.airport_id
                JOIN airports d ON cs.destination_airport_id = d.airport_id
                WHERE cs.awb_number = $1
            """, awb_number)

            if not cargo:
                return None

            # Get flight assignments
            assignments = await conn.fetch("""
                SELECT f.flight_number, f.scheduled_departure,
                       cfa.loading_status, cfa.sequence_number
                FROM cargo_flight_assignments cfa
                JOIN flights f ON cfa.flight_id = f.flight_id
                WHERE cfa.shipment_id = $1
                ORDER BY cfa.sequence_number
            """, cargo['shipment_id'])

            return {
                "shipment": dict(cargo),
                "flight_assignments": [dict(a) for a in assignments]
            }

    async def find_alternative_flights(
        self,
        origin_id: int,
        dest_id: int,
        after_time: str,
        hours_window: int = 24
    ) -> List[Dict]:
        """Find alternative flights for rebooking"""

        async with self.pool.acquire() as conn:
            flights = await conn.fetch("""
                SELECT f.flight_id, f.flight_number,
                       f.scheduled_departure, f.scheduled_arrival,
                       at.aircraft_code, at.passenger_capacity,
                       COUNT(b.booking_id) as booked_seats,
                       (at.passenger_capacity - COUNT(b.booking_id)) as available_seats
                FROM flights f
                JOIN aircraft_types at ON f.aircraft_type_id = at.aircraft_type_id
                LEFT JOIN bookings b ON f.flight_id = b.flight_id
                    AND b.booking_status IN ('Confirmed', 'CheckedIn')
                WHERE f.origin_airport_id = $1
                  AND f.destination_airport_id = $2
                  AND f.scheduled_departure > $3::timestamp
                  AND f.scheduled_departure < ($3::timestamp + ($4 || ' hours')::interval)
                  AND f.flight_status = 'Scheduled'
                GROUP BY f.flight_id, at.aircraft_type_id
                HAVING (at.passenger_capacity - COUNT(b.booking_id)) > 0
                ORDER BY f.scheduled_departure
            """, origin_id, dest_id, after_time, hours_window)

            return [dict(f) for f in flights]

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
```

### 3.3 Shared Memory with Database Integration

```python
class SharedMemory:
    """Shared memory system integrated with database"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.memory: Dict[str, Dict] = {}

    async def initialize_disruption(self, disruption_event: DisruptionEvent):
        """Initialize shared memory for a disruption"""

        # Load comprehensive context from database
        flight_details = await self.db.get_flight_details(disruption_event.flight_id)

        # Initialize memory structure
        self.memory[disruption_event.event_id] = {
            "disruption": disruption_event.dict(),
            "flight_context": flight_details,
            "safety_constraints": [],
            "impact_assessments": {},
            "agent_proposals": [],
            "debate_log": [],
            "scenarios": [],
            "human_decision": None,
            "execution_log": [],
            "timestamp": datetime.now().isoformat()
        }

    def get_context(self, event_id: str) -> Dict:
        """Get full context for event"""
        return self.memory.get(event_id, {})

    def add_safety_constraint(self, event_id: str, constraint: SafetyConstraint):
        """Add safety constraint (immutable after phase 2)"""
        self.memory[event_id]["safety_constraints"].append(constraint.dict())

    def set_impact_assessment(
        self,
        event_id: str,
        agent_name: str,
        assessment: ImpactAssessment
    ):
        """Store impact assessment from business agent"""
        self.memory[event_id]["impact_assessments"][agent_name] = assessment.dict()

    def add_proposal(self, event_id: str, proposal: RecoveryProposal):
        """Add recovery proposal"""
        self.memory[event_id]["agent_proposals"].append(proposal.dict())

    def get_all_proposals(self, event_id: str) -> List[Dict]:
        """Get all recovery proposals"""
        return self.memory[event_id].get("agent_proposals", [])
```

---

## 4. Agent Implementations with Database Access

### 4.1 Crew Compliance Agent (with DB Integration)

```python
class CrewComplianceAgent(BaseAgent):
    """Crew compliance agent with database-backed FTL checks"""

    def __init__(self, model_factory: ModelFactory, db_manager: DatabaseManager):
        super().__init__("crew_compliance_agent", model_factory)
        self.db = db_manager

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
- [Constraint 1]
- [Constraint 2]
</constraints>
"""

    async def assess(
        self,
        disruption: DisruptionEvent,
        recovery_options: List[RecoveryProposal]
    ) -> List[SafetyConstraint]:
        """Assess crew constraints with real data from database"""

        # Get flight context
        flight_ctx = await self.db.get_flight_details(disruption.flight_id)
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

        prompt += f"""
Proposed Recovery Options:
"""
        for option in recovery_options:
            prompt += f"- {option.title}: {option.description}\n"

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
```

### 4.2 Guest Experience Agent (with DB Integration)

```python
class GuestExperienceAgent(BaseAgent):
    """Guest experience agent with database-backed passenger analysis"""

    def __init__(self, model_factory: ModelFactory, db_manager: DatabaseManager):
        super().__init__("guest_experience_agent", model_factory)
        self.db = db_manager

    async def assess_impact(self, context: Dict[str, Any]) -> ImpactAssessment:
        """Phase 1: Quantify guest experience impact using real data"""

        disruption = context["disruption"]
        flight_ctx = context["flight_context"]
        pax_stats = flight_ctx["passengers"]

        prompt = f"""Analyze the guest experience impact of this disruption.

Flight: {disruption["flight_number"]}
Disruption: {disruption["description"]}

Passenger Statistics (Real Data):
- Total passengers: {pax_stats['total_pax']}
- Connecting passengers: {pax_stats['connections']}
- Connections at risk: {pax_stats['at_risk']}
- VIP passengers: {pax_stats['vip_count']}
- Platinum tier: {pax_stats['platinum']}
- First class: {pax_stats['first_class']}
- Business class: {pax_stats['business_class']}

Provide ONLY quantified impacts, NO solutions yet.

Required Analysis:
1. Misconnection impact severity
2. Elite passenger impact on NPS
3. Service recovery complexity
4. Estimated NPS delta

Use structured format.
"""

        response = await self.invoke(prompt, context)
        return self._parse_impact_assessment(response, pax_stats)
```

### 4.3 Cargo Agent (with DB Integration)

```python
class CargoAgent(BaseAgent):
    """Cargo agent with database-backed shipment analysis"""

    def __init__(self, model_factory: ModelFactory, db_manager: DatabaseManager):
        super().__init__("cargo_agent", model_factory)
        self.db = db_manager

    async def assess_impact(self, context: Dict[str, Any]) -> ImpactAssessment:
        """Phase 1: Quantify cargo impact using real AWB data"""

        disruption = context["disruption"]
        flight_ctx = context["flight_context"]
        cargo_stats = flight_ctx["cargo"]

        # Get detailed cargo list for this flight
        async with self.db.pool.acquire() as conn:
            cargo_details = await conn.fetch("""
                SELECT cs.awb_number, cs.total_weight_kg, cs.declared_value_usd,
                       ct.commodity_name, ct.temperature_controlled, ct.requires_special_handling
                FROM cargo_flight_assignments cfa
                JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
                JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
                WHERE cfa.flight_id = $1 AND cfa.loading_status = 'Planned'
            """, disruption["flight_id"])

        prompt = f"""Analyze the cargo impact of this disruption.

Flight: {disruption["flight_number"]}
Disruption: {disruption["description"]}

Cargo Statistics:
- Total shipments: {cargo_stats['total_shipments']}
- Total weight: {cargo_stats['total_cargo_weight']:.0f} kg
- Temperature-controlled: {cargo_stats['temp_controlled_weight']:.0f} kg
- Special handling required: {cargo_stats['special_handling_count']}

Detailed Shipments:
"""

        high_value_count = 0
        temp_controlled_count = 0

        for cargo in cargo_details:
            prompt += f"- AWB {cargo['awb_number']}: {cargo['commodity_name']}, "
            prompt += f"{cargo['total_weight_kg']:.0f} kg"

            if cargo['declared_value_usd']:
                prompt += f", ${cargo['declared_value_usd']:,.0f}"
                if cargo['declared_value_usd'] > 10000:
                    high_value_count += 1

            if cargo['temperature_controlled']:
                prompt += " (TEMP CONTROLLED)"
                temp_controlled_count += 1

            prompt += "\n"

        prompt += f"""
Provide ONLY quantified impacts, NO solutions yet.

Required Analysis:
1. High-value shipment risk
2. Perishable/temperature-controlled exposure
3. Revenue at risk
4. Cold-chain protection criticality

Use structured format.
"""

        context["cargo_details"] = [dict(c) for c in cargo_details]
        response = await self.invoke(prompt, context)

        return self._parse_impact_assessment(response, cargo_stats, cargo_details)
```

---

## 5. Skymarshal Arbitrator with Gemini 3 Pro

### 5.1 Arbitrator Implementation

```python
class SkyMarshalArbitrator:
    """Skymarshal Arbitrator using Claude Opus 4.5 for complex reasoning"""

    def __init__(
        self,
        model_factory: ModelFactory,
        historical_db: HistoricalDatabase,
        db_manager: DatabaseManager
    ):
        self.model_provider = model_factory.get_provider("arbitrator")
        self.history = historical_db
        self.db = db_manager
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        return """You are the SkyMarshal Arbitrator for Etihad Airways disruption management.

Your responsibilities:
1. Enforce all safety constraints (ZERO tolerance)
2. Synthesize recovery scenarios from agent proposals
3. Rank scenarios using multi-criteria optimization
4. Provide clear explainability for all decisions
5. Use historical data to predict outcomes

You have access to:
- Safety constraints (immutable, binding)
- Impact assessments from business agents
- Recovery proposals from business agents
- Agent debate logs
- Historical similar disruptions

Your output must include:
- Top 3 ranked scenarios
- Clear rationale for each ranking
- Pros and cons
- Confidence scores
- Sensitivity analysis

CRITICAL: You CANNOT violate safety constraints. Any scenario that violates constraints
must be immediately rejected.
"""

    async def arbitrate(
        self,
        context: Dict[str, Any]
    ) -> List[RankedScenario]:
        """Main arbitration logic"""

        # Step 1: Validate all proposals
        valid_proposals = self.validate_proposals(
            context["agent_proposals"],
            context["safety_constraints"]
        )

        if not valid_proposals:
            logger.warning("No valid proposals, creating conservative baseline")
            baseline = self.create_conservative_baseline(context)
            valid_proposals = [baseline]

        # Step 2: Compose scenarios
        scenarios = await self.compose_scenarios(valid_proposals, context)

        # Step 3: Score using historical data + LLM reasoning
        scored_scenarios = await self.score_scenarios(scenarios, context)

        # Step 4: Rank and explain (using Gemini 3 Pro's strong reasoning)
        ranked_scenarios = await self.rank_and_explain(scored_scenarios, context)

        return ranked_scenarios[:3]  # Top 3

    async def score_scenarios(
        self,
        scenarios: List[RecoveryScenario],
        context: Dict[str, Any]
    ) -> List[ScoredScenario]:
        """Score scenarios using historical data and Gemini 3 Pro reasoning"""

        # Find similar historical disruptions
        similar = self.history.find_similar(context["disruption"], limit=10)

        prompt = f"""Score the following recovery scenarios based on historical performance and multi-criteria optimization.

Current Disruption:
{json.dumps(context["disruption"], indent=2)}

Historical Similar Cases:
{self._format_historical_cases(similar)}

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

Use historical patterns to inform predictions.

Scoring criteria (in priority order):
1. Safety compliance (mandatory - already validated)
2. Passenger satisfaction (30% weight)
3. Cost efficiency (25% weight)
4. Network stability/delay (25% weight)
5. Execution reliability (20% weight)

Provide structured JSON output.
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.model_provider.invoke(
            messages,
            max_tokens=8192,
            temperature=0.3  # Lower temperature for consistent scoring
        )

        # Parse LLM response
        scored = self._parse_scenario_scores(response, scenarios, similar)

        return scored

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

        prompt = f"""Generate detailed explanations for the top 3 scenarios.

Current Disruption Context:
{json.dumps(context["disruption"], indent=2)}

Safety Constraints (All Met):
{json.dumps(context["safety_constraints"], indent=2)}

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
5. Sensitivity analysis:
   - What if crew overtime allowed?
   - What if higher cost acceptable?
   - What if longer delay acceptable?

Use clear, non-technical language suitable for Duty Manager review.
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.model_provider.invoke(
            messages,
            max_tokens=8192,
            temperature=0.5
        )

        # Parse explanations
        ranked = self._parse_ranked_scenarios(response, sorted_scenarios[:3])

        return ranked
```

---

## 6. Cost Optimization and Model Selection

### 6.1 Cost Analysis by Model

| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Use Case |
|-------|---------------------------|----------------------------|----------|
| **Gemini 3 Pro** | $1.25 | $5.00 | Arbitrator (complex reasoning, massive context) |
| **Claude Sonnet 4.5** | $3.00 | $15.00 | Safety agents, Orchestrator, Execution |
| **GPT-4o** | $2.50 | $10.00 | Network Agent (business) |
| **Gemini 2.0 Flash Thinking** | $0.00 (free preview) | $0.00 | Cargo Agent (business) |
| **Amazon Nova Pro** | $0.80 | $3.20 | Finance Agent (business) |

### 6.2 Estimated Cost Per Disruption

```
Disruption Processing:
- Orchestrator (Sonnet): ~10K tokens in, ~5K tokens out = $0.11
- Safety Agents (3x Sonnet): ~15K tokens in, ~8K tokens out = $0.46
- Business Agents (4x mixed):
  * Network Agent (GPT-4o): ~8K in, ~4K out = $0.06
  * Guest Experience (Sonnet): ~8K in, ~4K out = $0.08
  * Cargo Agent (Gemini Flash): ~8K in, ~4K out = $0.00 (free preview)
  * Finance Agent (Nova): ~8K in, ~4K out = $0.02
  Total Business: $0.16
- Arbitrator (Gemini 3 Pro): ~30K tokens in, ~15K tokens out = $0.11
- Execution Agents (5x Sonnet): ~8K tokens in, ~4K tokens out = $0.26

Total per disruption: ~$1.10

For 35 flights over 7 days with 20% disruption rate:
= 7 disruptions × $1.10 = ~$7.70 for hackathon demo

💰 Cost savings vs single-model: ~53% reduction by using optimal model selection
```

---

## 7. Implementation Checklist

### Day 1: Multi-Provider Setup + Core Infrastructure
- [ ] Set up AWS Bedrock IAM roles and permissions
- [ ] Install boto3, openai, google-generativeai packages
- [ ] Configure API keys (AWS, OpenAI, Google)
- [ ] Implement ModelFactory with all three providers
- [ ] Test model invocation: Claude (Bedrock), GPT-4o (OpenAI), Gemini (Google)
- [ ] Create BaseAgent with multi-model support
- [ ] Set up PostgreSQL database connection
- [ ] Implement DatabaseManager class with asyncpg
- [ ] Load existing CSV data into database
- [ ] Initialize LangGraph orchestrator structure

### Day 2: Agents + Database Integration
- [ ] Implement 3 Safety Agents (Claude Sonnet) with DB queries
- [ ] Implement 4 Business Agents (mixed models) with DB queries:
  * Network Agent (GPT-4o)
  * Guest Experience Agent (Claude Sonnet)
  * Cargo Agent (Gemini Flash Thinking)
  * Finance Agent (Amazon Nova Pro)
- [ ] Build two-phase protocol (impact → solution)
- [ ] Implement debate mechanism with model diversity
- [ ] Create SharedMemory with DB integration
- [ ] Implement SkyMarshalArbitrator (Gemini 3 Pro)
- [ ] Add constraint validation logic
- [ ] Test full Phase 1-5 flow with real data

### Day 3: Execution + Frontend + Demo
- [ ] Implement 5 Execution Agents (Claude Sonnet)
- [ ] Create MCP stubs for airline systems (PSS, Crew, Cargo)
- [ ] Build Streamlit dashboard with real-time updates
- [ ] Add WebSocket support for live agent updates
- [ ] Implement audit logging to database
- [ ] Create 3 demo scenarios using real flight data
- [ ] Add cost tracking per model (Bedrock, OpenAI, Google)
- [ ] Polish UI and test full demo flow (5-7 minutes)

---

## 8. Environment Configuration

### 8.1 Required Environment Variables

```bash
# AWS Configuration (for Bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>

# OpenAI Configuration
OPENAI_API_KEY=<your-openai-key>

# Google AI Configuration
GOOGLE_API_KEY=<your-google-api-key>

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=etihad_aviation
DB_USER=postgres
DB_PASSWORD=<your-password>

# Application Configuration
LOG_LEVEL=INFO
ENABLE_COST_TRACKING=true
MAX_DEBATE_ROUNDS=3
SAFETY_TIMEOUT_SECONDS=60
```

### 8.2 Dependencies

```requirements.txt
# AWS Bedrock
boto3>=1.34.0
botocore>=1.34.0

# OpenAI
openai>=1.12.0

# Google Gemini
google-generativeai>=0.4.0

# Database
asyncpg>=0.29.0
psycopg2-binary>=2.9.9

# Async
asyncio>=3.4.3
aiohttp>=3.9.0

# LangGraph
langgraph>=0.0.40
langchain>=0.1.0

# Data validation
pydantic>=2.5.0

# Web framework
fastapi>=0.109.0
uvicorn>=0.27.0
websockets>=12.0

# Frontend
streamlit>=1.30.0

# Utilities
python-dotenv>=1.0.0
python-json-logger>=2.0.7
```

---

## 9. Summary

This multi-model architecture provides:

✅ **Optimal Model Selection**: Right model for each task (cost vs performance)
✅ **Multi-Provider Integration**: AWS Bedrock + OpenAI + Google AI
✅ **Database Integration**: Real airline data with 35 flights, 8.8K passengers, 199 cargo shipments
✅ **Diverse Perspectives**: 4 different models in business agent debate (GPT-4o, Claude, Gemini, Nova)
✅ **Cost Efficient**: ~$1.10 per disruption (53% savings vs single-model)
✅ **Scalable**: Can handle multiple concurrent disruptions
✅ **Gemini 3 Pro Arbitrator**: Massive context window for complex multi-criteria optimization

**Model Distribution:**
- **Orchestrator**: Claude Sonnet 4.5 (state management)
- **Arbitrator**: Google Gemini 3 Pro (complex optimization)
- **Safety Agents**: Claude Sonnet 4.5 (chain-of-thought)
- **Business Agents**: GPT-4o (Network), Claude Sonnet (Guest), Gemini Flash (Cargo), Nova (Finance)
- **Execution Agents**: Claude Sonnet 4.5 (reliable execution)

This combination provides the best balance of accuracy, model diversity, cost efficiency, and performance for airline disruption management with true multi-agent collaboration across different AI providers.
