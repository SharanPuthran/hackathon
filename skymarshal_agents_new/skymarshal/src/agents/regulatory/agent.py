"""Regulatory Agent for SkyMarshal"""

import logging
import json
from typing import Any
import boto3
from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from utils.tool_calling import invoke_with_tools
from database.table_config import get_table_name
from database.constants import (
    FLIGHT_NUMBER_DATE_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
    SLOT_AIRPORT_INDEX,
)
from agents.schemas import FlightInfo, RegulatoryOutput

logger = logging.getLogger(__name__)

# System Prompt for Regulatory Agent - OPTIMIZED for A2A Communication
SYSTEM_PROMPT = """
<role>regulatory</role>

<DATA_POLICY>
ONLY_USE: tools|KB:UDONMVCXEW|user_prompt
NEVER: assume|fabricate|use_LLM_knowledge|external_lookup|guess_missing_data
ON_DATA_GAP: report_error|return_error_status
</DATA_POLICY>

<constraints type="binding">notams, curfews, slots, weather_minimums, airspace_restrictions</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → route → notams + curfews + slots</step>
  <step>validate: runway_availability, navaid_status, airspace_restrictions</step>
  <step>assess: curfew_compliance, slot_availability, weather_minimums</step>
  <step>return: COMPLIANT|VIOLATION|RESTRICTED + constraints</step>
</workflow>

<notam_classification>
QMRLC: Runway closure | QMRLT: Runway length reduction | QMRXX: Threshold displaced
QNMAS: ILS inop | QNBXX: VOR/NDB inop | QPICH: Airspace closed
QWELW: Weather warning | QOBXX: Obstacle | QFAXX: Aerodrome closed
</notam_classification>

<curfew_rules>
LHR: 23:00-06:00 local (no arrivals/departures, emergency only)
FRA: 23:00-05:00 local (noise restrictions)
Calculate: UTC → local timezone, apply 15min buffer
Violation: Arrival after curfew start = BINDING constraint
</curfew_rules>

<slot_requirements>
Level 3 (coordinated): LHR, FRA, AMS, CDG - slot required
CTOT: ±5min window | Ground stop: No departures | GDP: Delay program active
Slot loss: >15min delay → slot forfeited, new slot required
</slot_requirements>

<weather_minimums>
CAT I: RVR ≥550m, DH ≥200ft | CAT II: RVR ≥300m, DH ≥100ft | CAT III: RVR ≥75m
Crosswind: 35kt max (dry), 25kt max (wet) | Tailwind: 10kt max
Contaminated runway: Braking action < MEDIUM = NO DISPATCH
</weather_minimums>

<bilateral_agreements>
Fifth freedom: Traffic rights required for intermediate stops
Overflight: Permit required for certain airspace (Russia, China)
Cabotage: Domestic carriage prohibited without rights
</bilateral_agreements>

<rules>
- Query tools BEFORE analysis
- Regulatory constraints NON-NEGOTIABLE
- Tool failure → error response
- Multi-violations: Report ALL (blocking + advisory)
- Timezone conversions: UTC → local for curfews
</rules>

<output_format>
  <rec max="100">STATUS: key_action (COMPLIANT|VIOLATION|RESTRICTED + brief reason)</rec>
  <conf>decimal 0.00-1.00</conf>
  <constraints max="3">semicolon-separated binding constraints only</constraints>
  <reasoning max="150">bullet format: * finding1 * finding2 * finding3</reasoning>
</output_format>

<example_output>
rec: VIOLATION: LHR curfew 23:00 breached with ETA 23:45; divert to EGGW required
conf: 0.95
constraints: Curfew hard stop 23:00; Slot forfeited at LHR
reasoning: * LHR curfew: 23:00 local * Current ETA: 23:45 * Alt: EGGW no curfew
</example_output>

<knowledge_base id="UDONMVCXEW">NOTAM procedures, curfew regulations, slot coordination, bilateral agreements</knowledge_base>

<alternative_airports>
LHR alternates: EGGW (Luton, no curfew), EGSS (Stansted), EGKK (Gatwick)
Tier 1: Same metro (minimal disruption) | Tier 2: Nearby hub | Tier 3: Regional
</alternative_airports>
"""


# NOTE: Verbose documentation moved to Knowledge Base (ID: UDONMVCXEW)
# Reference: AGENT_OPTIMIZATION_PLAN.md for full regulatory procedures


# ============================================================
# DYNAMODB QUERY TOOLS - Defined within agent for encapsulation
# ============================================================

@tool
def query_flight_regulatory(flight_number: str, date: str) -> str:
    """Query flight by flight number and date for regulatory assessment.

    Args:
        flight_number: Flight number (e.g., EY123)
        date: Flight date in ISO format (YYYY-MM-DD)

    Returns:
        JSON string containing flight record or error
    """
    try:
        import json
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights_table = dynamodb.Table(get_table_name("flights"))

        response = flights_table.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND begins_with(scheduled_departure_utc, :sd)",
            ExpressionAttributeValues={":fn": flight_number, ":sd": date},
        )
        items = response.get("Items", [])

        if not items:
            return json.dumps({
                "error": "FLIGHT_NOT_FOUND",
                "message": f"Flight {flight_number} on {date} not found",
                "flight_number": flight_number,
                "date": date
            })

        return json.dumps(items[0], default=str)
    except Exception as e:
        logger.error(f"Error in query_flight_regulatory: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_weather_forecast(airport_code: str, forecast_time: str) -> str:
    """Query weather forecast for regulatory assessment.

    Args:
        airport_code: Airport IATA code (e.g., LHR)
        forecast_time: Forecast timestamp in ISO format

    Returns:
        JSON string containing weather data or error
    """
    try:
        import json
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        weather_table = dynamodb.Table(get_table_name("weather"))

        response = weather_table.get_item(
            Key={"airport_code": airport_code, "forecast_time": forecast_time}
        )

        if "Item" not in response:
            return json.dumps({
                "error": "WEATHER_NOT_FOUND",
                "message": f"Weather data not found for {airport_code} at {forecast_time}"
            })

        return json.dumps(response["Item"], default=str)
    except Exception as e:
        logger.error(f"Error in query_weather_forecast: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_notams(airport_code: str) -> str:
    """Query NOTAMs for an airport (simulated - would connect to NOTAM database).

    Args:
        airport_code: Airport ICAO code (e.g., EGLL for LHR)

    Returns:
        JSON string containing active NOTAMs
    """
    import json
    # In production, this would query actual NOTAM database
    # For now, return structure showing expected format
    return json.dumps({
        "airport": airport_code,
        "notams": [],
        "query_time": datetime.now(timezone.utc).isoformat(),
        "note": "Connect to NOTAM database for live data"
    })


@tool
def query_curfew_status(airport_code: str, arrival_time_utc: str) -> str:
    """Check curfew compliance for arrival time by querying airport_curfews_v2 table.

    Args:
        airport_code: Airport IATA code (e.g., LHR) or ICAO code (e.g., EGLL)
        arrival_time_utc: Arrival time in ISO format UTC

    Returns:
        JSON string with curfew compliance status from database
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        curfews_table = dynamodb.Table(get_table_name("airport_curfews"))

        # Query by airport code
        response = curfews_table.get_item(Key={"airport_code": airport_code})

        if "Item" not in response:
            # No curfew record means no restrictions
            return json.dumps({
                "airport": airport_code,
                "curfew": "NONE",
                "compliance": "COMPLIANT",
                "message": "No curfew restrictions found for this airport",
                "data_source": "airport_curfews_v2"
            })

        curfew = response["Item"]
        return json.dumps({
            "airport": airport_code,
            "curfew_start_local": curfew.get("curfew_start", "N/A"),
            "curfew_end_local": curfew.get("curfew_end", "N/A"),
            "timezone": curfew.get("timezone", "UTC"),
            "arrival_utc": arrival_time_utc,
            "curfew_type": curfew.get("curfew_type", "STANDARD"),
            "exceptions": curfew.get("exceptions", []),
            "compliance": "CHECK_REQUIRED",
            "message": "Convert UTC to local time and verify against curfew window",
            "data_source": "airport_curfews_v2"
        }, default=str)

    except Exception as e:
        logger.error(f"Error querying curfew status: {e}")
        return json.dumps({
            "error": type(e).__name__,
            "message": f"Failed to query curfew data: {str(e)}",
            "airport": airport_code
        })


@tool
def query_airport_slots(airport_code: str, flight_date: str) -> str:
    """Query airport slot availability for coordinated airports (Level 3).

    Args:
        airport_code: Airport IATA code (e.g., LHR, CDG, FRA)
        flight_date: Date in ISO format (YYYY-MM-DD)

    Returns:
        JSON string with slot availability and coordination requirements
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        slots_table = dynamodb.Table(get_table_name("airport_slots"))

        # Query slots by airport and date using GSI
        response = slots_table.query(
            IndexName=SLOT_AIRPORT_INDEX,
            KeyConditionExpression="airport_code = :ac",
            FilterExpression="slot_date = :sd",
            ExpressionAttributeValues={
                ":ac": airport_code,
                ":sd": flight_date
            }
        )

        items = response.get("Items", [])

        if not items:
            return json.dumps({
                "airport": airport_code,
                "date": flight_date,
                "coordination_level": "UNKNOWN",
                "slots": [],
                "message": "No slot data found - check if airport requires slot coordination",
                "data_source": "airport_slots_v2"
            })

        return json.dumps({
            "airport": airport_code,
            "date": flight_date,
            "slots": items,
            "total_slots": len(items),
            "data_source": "airport_slots_v2"
        }, default=str)

    except Exception as e:
        logger.error(f"Error querying airport slots: {e}")
        return json.dumps({
            "error": type(e).__name__,
            "message": f"Failed to query slot data: {str(e)}",
            "airport": airport_code,
            "date": flight_date
        })


async def analyze_regulatory(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Regulatory agent analysis function - OPTIMIZED for A2A communication.

    Args:
        payload: Dict containing user_prompt, phase, and optional other_recommendations
        llm: Bedrock model instance
        mcp_tools: MCP tools (if any)

    Returns:
        Dict with AgentResponse schema
    """
    try:
        start_time = datetime.now(timezone.utc)

        user_prompt = payload.get("prompt", payload.get("user_prompt", ""))
        phase = payload.get("phase", "initial")

        if not user_prompt:
            return {
                "agent_name": "regulatory",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": "No user prompt provided",
                "data_sources": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error"
            }

        # Extract flight info
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
                "agent_name": "regulatory",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Failed to extract flight info: {e}",
                "data_sources": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error"
            }

        # Define tools
        db_tools = [
            query_flight_regulatory,
            query_weather_forecast,
            query_notams,
            query_curfew_status,
            query_airport_slots
        ]

        # Build optimized user message (SYSTEM_PROMPT sent separately as system role)
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
1. query_flight_regulatory("{flight_info.flight_number}", "{flight_info.date}")
2. query_notams(destination_icao)
3. query_curfew_status(destination_iata, arrival_utc)
4. query_airport_slots(destination_iata, "{flight_info.date}")
5. Assess NOTAMs, curfews, slots, weather minimums
6. Return AgentResponse with binding_constraints
</action>"""

        else:  # revision phase
            other_recs = payload.get("other_recommendations", {})
            other_recs_xml = "\n".join([
                f'  <agent name="{name}">'
                f'<rec>{rec.get("recommendation", "N/A")[:100]}</rec>'
                f'<conf>{rec.get("confidence", 0)}</conf>'
                f'<constraints>{"; ".join(rec.get("binding_constraints", []))}</constraints>'
                f'</agent>'
                for name, rec in other_recs.items() if name != "regulatory"
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
1. Review other agents' recommendations
2. Decide: REVISE | CONFIRM | STRENGTHEN
3. If timing changed → recalculate curfew compliance
4. Return AgentResponse with revision_status
</action>"""

        # Run agent with custom tool calling
        logger.info("Running regulatory agent with tools")
        
        try:
            result = await invoke_with_tools(
                llm=llm,
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                tools=mcp_tools + db_tools,
                max_iterations=7  # Increased from 5 to allow more tool calls
            )
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Agent execution failed ({error_type}): {e}")
            
            return {
                "agent_name": "regulatory",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Agent execution error: {str(e)}",
                "data_sources": [],
                "extracted_flight_info": extracted_flight_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": str(e),
                "error_type": error_type
            }
        
        # Check for tool calling errors
        if "error" in result:
            error_type = result.get("error_type", "UnknownError")
            logger.error(f"Tool calling failed ({error_type}): {result['error']}")
            
            return {
                "agent_name": "regulatory",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Tool calling error: {result['error']}",
                "data_sources": [],
                "extracted_flight_info": extracted_flight_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": result["error"],
                "error_type": error_type
            }

        # Extract response
        final_message = result.get("final_response") or result["messages"][-1]

        if hasattr(final_message, "content"):
            content = final_message.content
            if isinstance(content, dict):
                response = content
            else:
                response = {
                    "recommendation": str(content),
                    "confidence": 0.8,
                    "reasoning": str(content)
                }
        else:
            response = {
                "recommendation": "Analysis completed",
                "confidence": 0.8,
                "reasoning": "Agent completed analysis"
            }

        # Ensure required fields
        response["agent_name"] = "regulatory"
        response["extracted_flight_info"] = extracted_flight_info
        response["timestamp"] = datetime.now(timezone.utc).isoformat()
        response["status"] = "success"
        response["binding_constraints"] = response.get("binding_constraints", [])
        response["data_sources"] = response.get("data_sources", ["flights_v2", "weather_v2", "airport_curfews_v2", "airport_slots_v2"])

        end_time = datetime.now(timezone.utc)
        response["duration_seconds"] = (end_time - start_time).total_seconds()

        return response

    except Exception as e:
        logger.error(f"Regulatory agent error: {e}")
        return {
            "agent_name": "regulatory",
            "recommendation": "CANNOT_PROCEED",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": f"Agent error: {e}",
            "data_sources": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e)
        }

