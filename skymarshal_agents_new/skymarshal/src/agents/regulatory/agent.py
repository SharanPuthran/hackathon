"""Regulatory Agent for SkyMarshal"""

import logging
import json
from typing import Any
import boto3
from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from utils.tool_calling import invoke_with_tools
from database.constants import (
    FLIGHTS_TABLE,
    CREW_ROSTER_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    WEATHER_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
)
from agents.schemas import FlightInfo, RegulatoryOutput

logger = logging.getLogger(__name__)

# System Prompt for Regulatory Agent - OPTIMIZED for A2A Communication
SYSTEM_PROMPT = """
<role>regulatory</role>

<CRITICAL_DATA_SOURCE_POLICY>
YOUR ONLY AUTHORITATIVE DATA SOURCES ARE:
1. Data returned by your tools (query_flight_regulatory, query_weather_forecast, query_notams, query_curfew_status)
2. Data from the Knowledge Base (ID: UDONMVCXEW)
3. Information explicitly provided in the user prompt

YOU MUST NEVER:
- Assume, infer, or fabricate ANY regulatory data not returned by tools
- Use your general LLM knowledge to fill in missing NOTAM, curfew, slot, or weather data
- Look up or reference external sources, websites, or APIs not provided as tools
- Make up NOTAM numbers, curfew times, slot allocations, weather minimums, or airspace restrictions
- Guess regulatory compliance status, permit requirements, or bilateral agreement terms when data is unavailable

If required data is unavailable from tools: REPORT THE DATA GAP and return error status.
VIOLATION OF THIS POLICY COMPROMISES REGULATORY COMPLIANCE AND FLIGHT SAFETY.
</CRITICAL_DATA_SOURCE_POLICY>

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
        flights_table = dynamodb.Table(FLIGHTS_TABLE)

        response = flights_table.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
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
        weather_table = dynamodb.Table(WEATHER_TABLE)

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
    """Check curfew compliance for arrival time.

    Args:
        airport_code: Airport ICAO code (e.g., EGLL)
        arrival_time_utc: Arrival time in ISO format UTC

    Returns:
        JSON string with curfew compliance status
    """
    import json
    from datetime import datetime as dt

    # Curfew database (would be in DynamoDB in production)
    curfews = {
        "EGLL": {"start": "23:00", "end": "06:00", "timezone": "Europe/London"},
        "EDDF": {"start": "23:00", "end": "05:00", "timezone": "Europe/Berlin"},
        "LFPG": {"start": "23:30", "end": "06:00", "timezone": "Europe/Paris"},
    }

    if airport_code not in curfews:
        return json.dumps({
            "airport": airport_code,
            "curfew": "NONE",
            "compliance": "COMPLIANT",
            "message": "No curfew restrictions at this airport"
        })

    curfew = curfews[airport_code]
    return json.dumps({
        "airport": airport_code,
        "curfew_start_local": curfew["start"],
        "curfew_end_local": curfew["end"],
        "timezone": curfew["timezone"],
        "arrival_utc": arrival_time_utc,
        "compliance": "CHECK_REQUIRED",
        "message": "Convert UTC to local time and verify against curfew window"
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
            query_curfew_status
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
3. query_curfew_status(destination_icao, arrival_utc)
4. Assess NOTAMs, curfews, slots, weather minimums
5. Return AgentResponse with binding_constraints
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
                max_iterations=5
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
        response["data_sources"] = response.get("data_sources", ["DynamoDB queries"])

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

