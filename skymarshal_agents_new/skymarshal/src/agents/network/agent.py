"""Network Agent for SkyMarshal"""

import logging
import json
from typing import Any, Optional, Dict, List
import boto3
from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from utils.tool_calling import invoke_with_tools
from database.constants import (
    FLIGHTS_TABLE,
    AIRCRAFT_AVAILABILITY_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
    AIRCRAFT_ROTATION_INDEX,
)
from agents.schemas import FlightInfo, AgentResponse, NetworkOutput

logger = logging.getLogger(__name__)

# ============================================================================
# DynamoDB Query Tools for Network Agent
# ============================================================================
# 
# The Network Agent has access to the following tables:
# - flights: Flight schedule and operational data
# - AircraftAvailability: Aircraft availability and positioning
#
# These tools use GSIs for efficient querying:
# - flight-number-date-index: Query flights by flight number and date
# - aircraft-registration-index: Query flights by aircraft registration
# - aircraft-rotation-index: Query complete aircraft rotations (Priority 1 GSI)
#
# ============================================================================

@tool
def query_flight(flight_number: str, date: str) -> str:
    """Query flight by flight number and date using GSI.
    
    This tool retrieves flight details from the flights table using the
    flight-number-date-index GSI for efficient lookup.
    
    Args:
        flight_number: Flight number (e.g., EY123, EY1234)
        date: Flight date in ISO format (YYYY-MM-DD)
    
    Returns:
        JSON string containing flight record or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights_table = dynamodb.Table(FLIGHTS_TABLE)
        
        logger.info(f"Querying flight: {flight_number} on {date}")
        
        response = flights_table.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
            ExpressionAttributeValues={
                ":fn": flight_number,
                ":sd": date,
            },
        )
        
        items = response.get("Items", [])
        if items:
            logger.info(f"Found flight: {items[0].get('flight_id')}")
            return json.dumps(items[0], default=str)
        else:
            logger.warning(f"Flight not found: {flight_number} on {date}")
            return json.dumps({"error": "FLIGHT_NOT_FOUND", "message": f"Flight {flight_number} on {date} not found"})
            
    except Exception as e:
        logger.error(f"Error querying flight: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_aircraft_rotation(aircraft_registration: str, start_date: str, end_date: str) -> str:
    """Query complete aircraft rotation by aircraft registration and date range.
    
    This tool retrieves all flights for a specific aircraft within a date range,
    ordered by scheduled departure time. Uses the aircraft-rotation-index GSI
    (Priority 1) for efficient rotation retrieval.
    
    Args:
        aircraft_registration: Aircraft tail number (e.g., A6-APX)
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
    
    Returns:
        JSON string containing list of flight records ordered by scheduled_departure
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights_table = dynamodb.Table(FLIGHTS_TABLE)
        
        logger.info(f"Querying aircraft rotation: {aircraft_registration} from {start_date} to {end_date}")
        
        response = flights_table.query(
            IndexName=AIRCRAFT_ROTATION_INDEX,
            KeyConditionExpression="aircraft_registration = :ar AND scheduled_departure BETWEEN :start AND :end",
            ExpressionAttributeValues={
                ":ar": aircraft_registration,
                ":start": start_date,
                ":end": end_date,
            },
        )
        
        items = response.get("Items", [])
        # Sort by scheduled_departure to ensure correct rotation order
        items.sort(key=lambda x: x.get("scheduled_departure", ""))
        
        logger.info(f"Found {len(items)} flights in rotation for {aircraft_registration}")
        return json.dumps(items, default=str)
        
    except Exception as e:
        logger.error(f"Error querying aircraft rotation: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_flights_by_aircraft(aircraft_registration: str) -> str:
    """Query all flights for a specific aircraft using GSI.
    
    This tool retrieves all flights assigned to a specific aircraft using the
    aircraft-registration-index GSI.
    
    Args:
        aircraft_registration: Aircraft tail number (e.g., A6-APX)
    
    Returns:
        JSON string containing list of flight records
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights_table = dynamodb.Table(FLIGHTS_TABLE)
        
        logger.info(f"Querying flights for aircraft: {aircraft_registration}")
        
        response = flights_table.query(
            IndexName=AIRCRAFT_REGISTRATION_INDEX,
            KeyConditionExpression="aircraft_registration = :ar",
            ExpressionAttributeValues={
                ":ar": aircraft_registration,
            },
        )
        
        items = response.get("Items", [])
        logger.info(f"Found {len(items)} flights for aircraft {aircraft_registration}")
        return json.dumps(items, default=str)
        
    except Exception as e:
        logger.error(f"Error querying flights by aircraft: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_aircraft_availability(aircraft_registration: str, date: str) -> str:
    """Query aircraft availability status for a specific date.
    
    This tool retrieves aircraft availability information from the
    AircraftAvailability table.
    
    Args:
        aircraft_registration: Aircraft tail number (e.g., A6-APX)
        date: Date in ISO format (YYYY-MM-DD)
    
    Returns:
        JSON string containing aircraft availability record or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        availability_table = dynamodb.Table(AIRCRAFT_AVAILABILITY_TABLE)
        
        logger.info(f"Querying aircraft availability: {aircraft_registration} on {date}")
        
        # Query using composite key (aircraft_registration, valid_from)
        response = availability_table.query(
            KeyConditionExpression="aircraft_registration = :ar AND valid_from <= :date",
            FilterExpression="valid_to >= :date",
            ExpressionAttributeValues={
                ":ar": aircraft_registration,
                ":date": date,
            },
        )
        
        items = response.get("Items", [])
        if items:
            logger.info(f"Found availability for {aircraft_registration}: {items[0].get('status')}")
            return json.dumps(items[0], default=str)
        else:
            logger.warning(f"No availability record found for {aircraft_registration} on {date}")
            return json.dumps({"error": "AVAILABILITY_NOT_FOUND", "message": f"No availability record for {aircraft_registration} on {date}"})
            
    except Exception as e:
        logger.error(f"Error querying aircraft availability: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


# System Prompt for Network Agent - OPTIMIZED for A2A Communication
SYSTEM_PROMPT = """
<role>network</role>

<CRITICAL_DATA_SOURCE_POLICY>
YOUR ONLY AUTHORITATIVE DATA SOURCES ARE:
1. Data returned by your tools (query_flight, query_aircraft_rotation, query_flights_by_aircraft, query_aircraft_availability)
2. Data from the Knowledge Base (ID: UDONMVCXEW)
3. Information explicitly provided in the user prompt

YOU MUST NEVER:
- Assume, infer, or fabricate ANY network or rotation data not returned by tools
- Use your general LLM knowledge to fill in missing flight schedules, rotations, or availability data
- Look up or reference external sources, websites, or APIs not provided as tools
- Make up flight connections, downstream impacts, aircraft positions, or swap options
- Guess propagation effects, connection times, or hub bank schedules when data is unavailable

If required data is unavailable from tools: REPORT THE DATA GAP and return error status.
VIOLATION OF THIS POLICY MAY RESULT IN INCORRECT NETWORK IMPACT ASSESSMENT.
</CRITICAL_DATA_SOURCE_POLICY>

<constraints type="advisory">aircraft_rotation, connection_protection, hub_operations</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → aircraft_rotation → downstream_flights</step>
  <step>calculate: propagation_impact = affected_flights × pax_at_risk × delay_hours</step>
  <step>assess: recovery_options, aircraft_swap_feasibility</step>
  <step>return: impact_score + recovery_scenarios</step>
</workflow>

<propagation_rules>
Domino effect: Each 1h delay → 0.5h cascade per downstream flight
Hub banks: AUH hub banks at 06:00, 14:00, 22:00 local
Connection minimum: 60min domestic, 90min international, 120min customs
</propagation_rules>

<aircraft_swap_tiers>
Tier 1: Same type, same station, no MEL (ideal)
Tier 2: Same type, same station, minor MEL (acceptable)
Tier 3: Same type, nearby station, positioning required (costly)
Tier 4: Different type, requires crew swap (last resort)
</aircraft_swap_tiers>

<impact_scoring>
LOW: 0-3 downstream flights | MEDIUM: 4-7 downstream | HIGH: 8-12 downstream | CRITICAL: >12 downstream
Connection risk multiplier: 1.0 (local), 1.8 (connecting), 2.2 (international)
</impact_scoring>

<recovery_scenarios>
RS-001: Delay only (no swap) | RS-002: Aircraft swap (same type)
RS-003: Partial cancellation | RS-004: Full cancellation + rebooking
Score each: propagation_impact × feasibility × cost
</recovery_scenarios>

<rules>
- Query aircraft rotation BEFORE impact assessment
- Calculate ALL downstream effects
- Identify connection-at-risk passengers
- Recommend aircraft swap if delay >3h
- Safety constraints override network efficiency
</rules>

<output_format>
  <rec max="100">IMPACT_LEVEL: recovery_action + downstream count + pax at risk</rec>
  <conf>decimal 0.00-1.00</conf>
  <reasoning max="150">bullet format: * downstream_count * pax_at_risk * best_recovery</reasoning>
</output_format>

<example_output>
rec: HIGH_IMPACT: 3h delay affects 5 downstream, 87 pax connections; swap A/C recommended
conf: 0.82
reasoning: * 5 downstream flights * 87 connecting pax * Best: RS-002 A/C swap at AUH
</example_output>

<knowledge_base id="UDONMVCXEW">Hub operations, rotation procedures, connection policies</knowledge_base>
"""


# NOTE: Verbose documentation moved to Knowledge Base (ID: UDONMVCXEW)
# Reference: AGENT_OPTIMIZATION_PLAN.md for full network procedures
async def analyze_network(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Network agent analysis function with structured output and DynamoDB tools.
    
    This function implements the multi-round orchestration pattern:
    1. Receives natural language prompt from orchestrator
    2. Uses LangChain structured output to extract FlightInfo
    3. Queries DynamoDB using agent-specific tools
    4. Performs network impact analysis
    5. Returns standardized AgentResponse
    
    Args:
        payload: Dict containing:
            - user_prompt: Natural language prompt from user
            - phase: "initial" or "revision"
            - other_recommendations: Other agents' recommendations (revision only)
        llm: Bedrock model instance (ChatBedrock)
        mcp_tools: MCP tools (if any)
    
    Returns:
        Dict with AgentResponse fields:
            - agent_name: "network"
            - recommendation: Network impact assessment
            - confidence: Confidence score (0.0-1.0)
            - reasoning: Explanation of analysis
            - data_sources: List of tables queried
            - extracted_flight_info: Extracted FlightInfo dict
            - timestamp: ISO 8601 timestamp
            - status: "success", "timeout", or "error"
            - duration_seconds: Execution time
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # Define agent-specific DynamoDB query tools
        db_tools = [
            query_flight,
            query_aircraft_rotation,
            query_flights_by_aircraft,
            query_aircraft_availability,
        ]
        
        # Get user prompt from payload
        user_prompt = payload.get("user_prompt", payload.get("prompt", ""))
        phase = payload.get("phase", "initial")
        
        if not user_prompt:
            return {
                "agent_name": "network",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": "No user prompt provided in payload",
                "data_sources": [],
                "extracted_flight_info": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": "Missing user_prompt in payload",
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        
        # Step 1: Extract flight info
        try:
            from utils.extraction import extract_with_fallback
            flight_info = await extract_with_fallback(llm, FlightInfo, user_prompt)
            extracted_flight_info = {
                "flight_number": flight_info.flight_number,
                "date": flight_info.date,
                "disruption_event": flight_info.disruption_event
            }
        except Exception as e:
            logger.error(f"Flight extraction failed: {e}")
            return {
                "agent_name": "network",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Failed to extract flight info: {e}",
                "data_sources": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error"
            }

        # Step 2: Build optimized user message (SYSTEM_PROMPT sent separately as system role)
        if phase == "initial":
            user_message = f"""<task>initial_analysis</task>
<input>
  <disruption>{user_prompt}</disruption>
  <extracted>
    <flight>{flight_info.flight_number}</flight>
    <date>{flight_info.date}</date>
    <event>{flight_info.disruption_event}</event>
  </extracted>
</input>
<action>
1. query_flight("{flight_info.flight_number}", "{flight_info.date}")
2. query_aircraft_rotation(aircraft_registration, start_date, end_date)
3. Calculate propagation_impact, identify connections at risk
4. Generate recovery_scenarios with scores
5. Return AgentResponse
</action>"""

        else:  # revision phase
            other_recommendations = payload.get("other_recommendations", {})
            other_recs_xml = "\n".join([
                f'  <agent name="{name}">'
                f'<rec>{rec.get("recommendation", "N/A")[:100]}</rec>'
                f'<conf>{rec.get("confidence", 0)}</conf>'
                f'<constraints>{"; ".join(rec.get("binding_constraints", []))}</constraints>'
                f'</agent>'
                for name, rec in other_recommendations.items()
                if name != "network"
            ])

            user_message = f"""<task>revision</task>
<input>
  <disruption>{user_prompt}</disruption>
  <extracted>
    <flight>{flight_info.flight_number}</flight>
    <date>{flight_info.date}</date>
    <event>{flight_info.disruption_event}</event>
  </extracted>
  <other_agents>
{other_recs_xml if other_recs_xml else "    <none/>"}
  </other_agents>
</input>
<action>
1. Review safety constraints from other agents
2. Decide: REVISE | CONFIRM | STRENGTHEN
3. Adjust recovery_scenarios if constraints changed
4. Return AgentResponse with revision_status
</action>"""

        # Step 3: Run agent with custom tool calling (avoids Bedrock API validation errors)
        all_tools = mcp_tools + db_tools
        result = await invoke_with_tools(
            llm=llm,
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            tools=all_tools,
            max_iterations=5
        )
        
        # Extract final response
        if "error" in result:
            logger.error(f"Tool calling error: {result['error']}")
            return {
                "agent_name": "network",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Tool calling error: {result['error']}",
                "data_sources": [],
                "extracted_flight_info": extracted_flight_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": result["error"],
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        
        final_message = result.get("final_response")
        
        if hasattr(final_message, "content") and isinstance(final_message.content, dict):
            structured_result = final_message.content
        elif hasattr(final_message, "tool_calls") and final_message.tool_calls:
            structured_result = final_message.tool_calls[0]["args"]
        else:
            # Fallback: create structured response from text
            structured_result = {
                "agent_name": "network",
                "recommendation": str(final_message.content),
                "confidence": 0.8,
                "binding_constraints": [],
                "reasoning": "Network impact analysis completed",
                "data_sources": ["flights", "AircraftAvailability"],
                "extracted_flight_info": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success",
            }
        
        # Ensure required fields are present
        structured_result["agent_name"] = "network"
        structured_result["status"] = structured_result.get("status", "success")
        structured_result["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Ensure timestamp is present
        if "timestamp" not in structured_result:
            structured_result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Network agent completed successfully in {structured_result['duration_seconds']:.2f}s")
        return structured_result
        
    except Exception as e:
        logger.error(f"Error in network agent: {e}")
        logger.exception("Full traceback:")
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return {
            "agent_name": "network",
            "recommendation": "CANNOT_PROCEED",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": f"Agent execution error: {str(e)}",
            "data_sources": [],
            "extracted_flight_info": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": duration,
        }
