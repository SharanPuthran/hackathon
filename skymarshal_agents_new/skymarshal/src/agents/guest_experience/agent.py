"""Guest Experience Agent for SkyMarshal"""

import boto3
import json
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from utils.tool_calling import invoke_with_tools
from agents.schemas import GuestExperienceOutput, FlightInfo
from database.table_config import get_table_name
from database.constants import (
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_ID_INDEX,
    BOOKING_INDEX,
    PASSENGER_FLIGHT_INDEX,
    FLIGHT_STATUS_INDEX,
    LOCATION_STATUS_INDEX,
    PASSENGER_ELITE_TIER_INDEX,
    REGULATION_INDEX,
    ROUTE_INDEX,
    FIRST_LEG_FLIGHT_INDEX,
)
import logging
from typing import Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

# System Prompt for Guest Experience Agent - UPDATED for Multi-Round Orchestration
SYSTEM_PROMPT = """
<role>Guest Experience: assess passenger impact, compensation, reprotection options</role>

<DATA_POLICY>
ONLY_USE: tools|KB:UDONMVCXEW|user_prompt
NEVER: assume|fabricate|use_LLM_knowledge|external_lookup|guess_missing_data
ON_DATA_GAP: report_error|return_error_status
</DATA_POLICY>

<workflow>
1. Extract: flight_number, date, event from user prompt
2. Query: query_flight() → passenger_manifest, then segment passengers by tier/connection status
3. Segment: High-value (elite status), connections, special needs
4. Calculate: Impact severity (delay hours × pax count × tier multiplier)
5. Estimate: Compensation costs (EU261, DOT, Etihad policy)
6. Propose: Reprotection options (alternative flights, hotels, refunds)
7. Return: Impact assessment with compensation_cost, reprotection_plan
</workflow>

<impact_severity>
severity = delay_hours × affected_pax × loyalty_multiplier × connection_risk
loyalty_multiplier: Guest (1.0) | Silver (1.2) | Gold (1.5) | Platinum (2.0)
connection_risk: Local (1.0) | Connecting (1.8) | International (2.2)
</impact_severity>

<compensation_rules>
EU261: >3h delay → €250-600 | Cancellation → Full refund + compensation
DOT: Involuntary denied boarding → 200-400% ticket price
Etihad: Proactive offers for high-value passengers
</compensation_rules>

<rules>
- Query tools BEFORE analysis (never assume data)
- Prioritize high-value passengers in reprotection
- Calculate compensation accurately per jurisdiction
- If tools fail: Return error response
</rules>

<output_format>
  <rec max="100">IMPACT_LEVEL: affected_pax count + compensation estimate + top priority action</rec>
  <conf>decimal 0.00-1.00</conf>
  <reasoning max="150">bullet format: * pax_count * comp_cost * reprotection_action</reasoning>
</output_format>

<example_output>
rec: HIGH_IMPACT: 285 pax affected, €45K compensation; prioritize 12 Platinum rebooking
conf: 0.85
reasoning: * 285 pax total * 12 Platinum tier * EU261: €42K * Hotels: €3K
</example_output>

<knowledge_base id="UDONMVCXEW">Query for passenger rights, compensation policies, rebooking options, service recovery</knowledge_base>
"""


# ============================================================================
# DynamoDB Query Tools
# ============================================================================
#
# Each agent defines its own DynamoDB query tools directly in its agent.py file
# using the @tool decorator. There is NO centralized tool factory or shared tool
# module. Tools are co-located with agent logic for better encapsulation.
#
# The @tool decorator is the recommended LangChain pattern for creating tools.
# It automatically creates Tool objects from functions with type hints and
# docstrings.
#
# Guest Experience Agent is authorized to access:
# - flights: Flight details and schedules
# - bookings: Passenger bookings and reservations
# - Baggage: Baggage tracking and status
# - passengers: Passenger profiles and loyalty information
#
# Guest Experience Agent uses these GSIs:
# - flight-number-date-index: Query flights by flight number and date
# - flight-id-index: Query bookings by flight ID
# - booking-index: Query baggage by booking ID
# - passenger-flight-index: Query bookings by passenger ID (Priority 1)
# - flight-status-index: Query bookings by flight and status (Priority 1)
# - location-status-index: Query baggage by location and status
# - passenger-elite-tier-index: Query passengers by elite tier (Priority 1)
# ============================================================================


def _convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


@tool
def query_flight(flight_number: str, date: str) -> str:
    """Query flight by flight number and date using GSI.

    This tool retrieves flight details including aircraft registration, departure/arrival
    times, and flight status. Use this as the first step to get the flight_id for
    subsequent queries.

    Args:
        flight_number: Flight number (e.g., EY123)
        date: Flight date in ISO format (YYYY-MM-DD)

    Returns:
        JSON string containing flight record or error
    """
    try:
        flights_table = dynamodb.Table(get_table_name("flights"))

        response = flights_table.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND begins_with(scheduled_departure_utc, :sd)",
            ExpressionAttributeValues={":fn": flight_number, ":sd": date},
        )

        items = response.get("Items", [])
        if items:
            result = _convert_decimals(items[0])
            logger.info(
                f"Found flight {flight_number} on {date}: flight_id={result.get('flight_id')}"
            )
            return json.dumps(result, default=str)
        else:
            logger.warning(f"Flight {flight_number} on {date} not found")
            return json.dumps({"error": "FLIGHT_NOT_FOUND", "message": f"Flight {flight_number} on {date} not found"})

    except Exception as e:
        logger.error(f"Error querying flight {flight_number} on {date}: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_bookings_by_flight(flight_id: str) -> str:
    """Query all passengers for a flight using V2 passengers table with first-leg-flight-index GSI.

    This tool retrieves all passengers for a specific flight, including
    passenger IDs, booking status, cabin class, PNR, and frequent flyer tier.
    Uses passengers_v2 table with first-leg-flight-index GSI for proper V2 data access.

    Args:
        flight_id: Unique flight identifier (e.g., "FLT-2001")

    Returns:
        JSON string containing list of passenger records
    """
    try:
        # Use passengers_v2 table with first-leg-flight-index GSI
        # V1 bookings table uses numeric flight_id, but V2 passengers_v2 uses string format
        passengers_table = dynamodb.Table(get_table_name("passengers"))

        response = passengers_table.query(
            IndexName=FIRST_LEG_FLIGHT_INDEX,
            KeyConditionExpression="first_leg_flight_id = :fid",
            ExpressionAttributeValues={":fid": flight_id},
        )

        items = _convert_decimals(response.get("Items", []))
        logger.info(f"Found {len(items)} passengers for flight {flight_id}")
        return json.dumps(items, default=str)

    except Exception as e:
        logger.error(f"Error querying passengers for flight {flight_id}: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_bookings_by_passenger(passenger_id: str, flight_id: Optional[str] = None) -> str:
    """Query passenger bookings by passenger ID using GSI (Priority 1).

    This tool retrieves booking history for a specific passenger, optionally filtered
    by flight ID. Useful for identifying frequent flyers and booking patterns.

    Args:
        passenger_id: Unique passenger identifier
        flight_id: Optional flight ID to filter bookings

    Returns:
        JSON string containing list of booking records
    """
    try:
        bookings_table = dynamodb.Table(get_table_name("bookings"))

        if flight_id:
            response = bookings_table.query(
                IndexName=PASSENGER_FLIGHT_INDEX,
                KeyConditionExpression="passenger_id = :pid AND flight_id = :fid",
                ExpressionAttributeValues={":pid": passenger_id, ":fid": flight_id},
            )
        else:
            response = bookings_table.query(
                IndexName=PASSENGER_FLIGHT_INDEX,
                KeyConditionExpression="passenger_id = :pid",
                ExpressionAttributeValues={":pid": passenger_id},
            )

        items = _convert_decimals(response.get("Items", []))
        logger.info(f"Found {len(items)} bookings for passenger {passenger_id}")
        return json.dumps(items, default=str)

    except Exception as e:
        logger.error(f"Error querying bookings for passenger {passenger_id}: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_bookings_by_status(flight_id: str, booking_status: str) -> str:
    """Query bookings by flight and status using GSI (Priority 1).

    This tool retrieves bookings filtered by status (e.g., confirmed, cancelled, standby).
    Useful for generating passenger manifests and identifying affected passengers.

    Args:
        flight_id: Unique flight identifier
        booking_status: Booking status (e.g., "confirmed", "cancelled", "standby")

    Returns:
        JSON string containing list of booking records
    """
    try:
        bookings_table = dynamodb.Table(get_table_name("bookings"))

        response = bookings_table.query(
            IndexName=FLIGHT_STATUS_INDEX,
            KeyConditionExpression="flight_id = :fid AND booking_status = :status",
            ExpressionAttributeValues={":fid": flight_id, ":status": booking_status},
        )

        items = _convert_decimals(response.get("Items", []))
        logger.info(
            f"Found {len(items)} {booking_status} bookings for flight {flight_id}"
        )
        return json.dumps(items, default=str)

    except Exception as e:
        logger.error(
            f"Error querying {booking_status} bookings for flight {flight_id}: {e}"
        )
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_baggage_by_booking(booking_id: str) -> str:
    """Query baggage by booking ID using GSI.

    This tool retrieves all baggage records for a specific booking, including
    baggage tags, current location, and status.

    Args:
        booking_id: Unique booking identifier

    Returns:
        JSON string containing list of baggage records
    """
    try:
        baggage_table = dynamodb.Table(get_table_name("baggage"))

        response = baggage_table.query(
            IndexName=BOOKING_INDEX,
            KeyConditionExpression="booking_id = :bid",
            ExpressionAttributeValues={":bid": booking_id},
        )

        items = _convert_decimals(response.get("Items", []))
        logger.info(f"Found {len(items)} baggage items for booking {booking_id}")
        return json.dumps(items, default=str)

    except Exception as e:
        logger.error(f"Error querying baggage for booking {booking_id}: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_baggage_by_location(current_location: str, baggage_status: Optional[str] = None) -> str:
    """Query baggage by location and status using GSI.

    This tool retrieves baggage at a specific location, optionally filtered by status.
    Useful for tracking mishandled baggage and location-based queries.

    Args:
        current_location: Airport code or location identifier
        baggage_status: Optional status filter (e.g., "checked", "loaded", "mishandled")

    Returns:
        JSON string containing list of baggage records
    """
    try:
        baggage_table = dynamodb.Table(get_table_name("baggage"))

        if baggage_status:
            response = baggage_table.query(
                IndexName=LOCATION_STATUS_INDEX,
                KeyConditionExpression="current_location = :loc AND baggage_status = :status",
                ExpressionAttributeValues={
                    ":loc": current_location,
                    ":status": baggage_status,
                },
            )
        else:
            response = baggage_table.query(
                IndexName=LOCATION_STATUS_INDEX,
                KeyConditionExpression="current_location = :loc",
                ExpressionAttributeValues={":loc": current_location},
            )

        items = _convert_decimals(response.get("Items", []))
        logger.info(
            f"Found {len(items)} baggage items at {current_location}"
            + (f" with status {baggage_status}" if baggage_status else "")
        )
        return json.dumps(items, default=str)

    except Exception as e:
        logger.error(f"Error querying baggage at {current_location}: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_passenger(passenger_id: str) -> str:
    """Query passenger details by passenger ID.

    This tool retrieves passenger profile information including name, contact details,
    frequent flyer status, and loyalty tier.

    Args:
        passenger_id: Unique passenger identifier

    Returns:
        JSON string containing passenger record or error
    """
    try:
        passengers_table = dynamodb.Table(get_table_name("passengers"))

        response = passengers_table.get_item(Key={"passenger_id": passenger_id})

        item = response.get("Item")
        if item:
            result = _convert_decimals(item)
            logger.info(f"Found passenger {passenger_id}")
            return json.dumps(result, default=str)
        else:
            logger.warning(f"Passenger {passenger_id} not found")
            return json.dumps({"error": "PASSENGER_NOT_FOUND", "message": f"Passenger {passenger_id} not found"})

    except Exception as e:
        logger.error(f"Error querying passenger {passenger_id}: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_elite_passengers(frequent_flyer_tier: str, booking_date_from: Optional[str] = None) -> str:
    """Query passengers by elite tier using GSI (Priority 1).

    This tool retrieves passengers by frequent flyer tier, optionally filtered by
    booking date. Useful for identifying VIP passengers and elite status holders.

    Args:
        frequent_flyer_tier: Tier identifier (e.g., "SILVER", "GOLD", "PLATINUM", "DIAMOND")
        booking_date_from: Optional minimum booking date in ISO format (YYYY-MM-DD)

    Returns:
        JSON string containing list of passenger records
    """
    try:
        passengers_table = dynamodb.Table(get_table_name("passengers"))

        if booking_date_from:
            response = passengers_table.query(
                IndexName=PASSENGER_ELITE_TIER_INDEX,
                KeyConditionExpression="frequent_flyer_tier = :tier AND passenger_id >= :date",
                ExpressionAttributeValues={
                    ":tier": frequent_flyer_tier,
                    ":date": booking_date_from,
                },
            )
        else:
            response = passengers_table.query(
                IndexName=PASSENGER_ELITE_TIER_INDEX,
                KeyConditionExpression="frequent_flyer_tier = :tier",
                ExpressionAttributeValues={":tier": frequent_flyer_tier},
            )

        items = _convert_decimals(response.get("Items", []))
        logger.info(f"Found {len(items)} passengers with tier {frequent_flyer_tier}")
        return json.dumps(items, default=str)

    except Exception as e:
        logger.error(f"Error querying elite passengers with tier {frequent_flyer_tier}: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_compensation_rules(regulation: str, delay_category: str) -> str:
    """Query compensation rules by regulation and delay category.

    This tool retrieves passenger compensation requirements based on
    applicable regulation (EU261, DOT, etc.) and delay duration.

    Args:
        regulation: Regulatory framework (e.g., "EU261", "DOT", "GCAA")
        delay_category: Delay category (e.g., "2-3h", "3-4h", ">4h", "cancellation")

    Returns:
        JSON string containing compensation rules or error
    """
    try:
        comp_table = dynamodb.Table(get_table_name("compensation_rules"))

        logger.info(f"Querying compensation rules: {regulation} / {delay_category}")

        # Use regulation-index GSI with filter on delay_category
        # Table PK is rule_id, so we must use GSI for regulation lookup
        response = comp_table.query(
            IndexName=REGULATION_INDEX,
            KeyConditionExpression="regulation = :reg",
            FilterExpression="delay_category = :dc",
            ExpressionAttributeValues={
                ":reg": regulation,
                ":dc": delay_category
            }
        )

        items = response.get("Items", [])
        if items:
            result = _convert_decimals(items[0])
            logger.info(f"Found compensation rules for {regulation}/{delay_category}")
            return json.dumps(result, default=str)
        else:
            logger.warning(f"Compensation rules not found for {regulation}/{delay_category}")
            return json.dumps({
                "error": "RULES_NOT_FOUND",
                "message": f"No compensation rules for {regulation} at {delay_category}",
                "data_source": "compensation_rules_v2"
            })

    except Exception as e:
        logger.error(f"Error querying compensation rules: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_oal_flights(origin: str, destination: str, date: str) -> str:
    """Query Other Airline (OAL) flights for rebooking passengers.

    This tool retrieves available flights from interline partner airlines
    for passenger rebooking options.

    Args:
        origin: Origin airport IATA code (e.g., AUH, LHR)
        destination: Destination airport IATA code
        date: Flight date in ISO format (YYYY-MM-DD)

    Returns:
        JSON string containing list of OAL flight options
    """
    try:
        oal_table = dynamodb.Table(get_table_name("oal_flights"))

        logger.info(f"Querying OAL flights: {origin} → {destination} on {date}")

        response = oal_table.query(
            IndexName=ROUTE_INDEX,
            KeyConditionExpression="origin = :o AND destination = :d",
            FilterExpression="flight_date = :fd",
            ExpressionAttributeValues={
                ":o": origin,
                ":d": destination,
                ":fd": date
            }
        )

        items = _convert_decimals(response.get("Items", []))
        logger.info(f"Found {len(items)} OAL flights for {origin}-{destination}")
        return json.dumps({
            "origin": origin,
            "destination": destination,
            "date": date,
            "oal_flights": items,
            "total_options": len(items),
            "data_source": "oal_flights_v2"
        }, default=str)

    except Exception as e:
        logger.error(f"Error querying OAL flights: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


async def analyze_guest_experience(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Guest Experience agent analysis function with natural language prompt support.
    
    This agent:
    1. Receives natural language prompts from the orchestrator
    2. Uses LangChain structured output to extract flight information
    3. Queries DynamoDB using agent-specific tools
    4. Generates passenger impact assessment and recommendations
    
    The agent is responsible for:
    - Extracting flight number, date, and disruption details from the prompt
    - Querying passenger bookings and baggage data
    - Identifying high-value and vulnerable passengers
    - Predicting NPS impact and defection risk
    - Generating rebooking options and service recovery recommendations
    
    Args:
        payload: Dict containing:
            - user_prompt: Natural language disruption description
            - phase: "initial" or "revision"
            - other_recommendations: Other agents' recommendations (revision only)
        llm: Bedrock model instance (ChatBedrock)
        mcp_tools: MCP tools (if any)
    
    Returns:
        Dict with agent response including recommendation, confidence, reasoning, etc.
    """
    try:
        # Define agent-specific DynamoDB query tools
        db_tools = [
            query_flight,
            query_bookings_by_flight,
            query_bookings_by_passenger,
            query_bookings_by_status,
            query_baggage_by_booking,
            query_baggage_by_location,
            query_passenger,
            query_elite_passengers,
            query_compensation_rules,
            query_oal_flights,
        ]

        # Get user prompt from payload
        user_prompt = payload.get("user_prompt", payload.get("prompt", ""))
        phase = payload.get("phase", "initial")
        other_recommendations = payload.get("other_recommendations")

        # Step 1: Extract flight info
        try:
            from utils.extraction import extract_with_fallback
            from agents.schemas import FlightInfo
            flight_info = await extract_with_fallback(llm, FlightInfo, user_prompt)
            extracted_flight_info = {
                "flight_number": flight_info.flight_number,
                "date": flight_info.date,
                "disruption_event": flight_info.disruption_event
            }
        except Exception as e:
            logger.error(f"Flight extraction failed: {e}")
            return {
                "agent": "guest_experience",
                "category": "business",
                "assessment": "CANNOT_PROCEED",
                "status": "error",
                "failure_reason": f"Failed to extract flight info: {e}",
                "recommendations": ["Please provide flight number and date in your prompt."],
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
2. query_bookings_by_flight(flight_id)
3. Segment passengers: elite tier, connections, special needs
4. Calculate impact_severity, estimate compensation
5. Return AgentResponse
</action>"""

        else:  # revision phase
            other_recs = other_recommendations or {}
            other_recs_xml = "\n".join([
                f'  <agent name="{name}">'
                f'<rec>{rec.get("recommendation", "N/A")[:100]}</rec>'
                f'<conf>{rec.get("confidence", 0)}</conf>'
                f'<constraints>{"; ".join(rec.get("binding_constraints", []))}</constraints>'
                f'</agent>'
                for name, rec in other_recs.items()
                if name != "guest_experience"
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
3. Update rebooking options if timing changed
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
                "agent": "guest_experience",
                "category": "business",
                "assessment": "CANNOT_PROCEED",
                "status": "error",
                "failure_reason": f"Tool calling error: {result['error']}",
                "error": result["error"],
                "recommendations": ["Agent encountered an error and cannot proceed."],
            }
        
        final_message = result.get("final_response")

        # Extract structured output

        if hasattr(final_message, "content") and isinstance(
            final_message.content, dict
        ):
            structured_result = final_message.content
        elif hasattr(final_message, "tool_calls") and final_message.tool_calls:
            structured_result = final_message.tool_calls[0]["args"]
        else:
            structured_result = {
                "agent": "guest_experience",
                "category": "business",
                "result": str(final_message.content),
                "status": "success",
            }
        
        # Ensure required fields are present
        structured_result["agent"] = "guest_experience"
        structured_result["category"] = "business"
        if "status" not in structured_result:
            structured_result["status"] = "success"

        logger.info(f"Guest Experience agent completed successfully in {phase} phase")
        return structured_result

    except Exception as e:
        logger.error(f"Error in guest_experience agent: {e}")
        logger.exception("Full traceback:")
        return {
            "agent": "guest_experience",
            "category": "business",
            "assessment": "CANNOT_PROCEED",
            "status": "error",
            "failure_reason": f"Agent execution error: {str(e)}",
            "error": str(e),
            "error_type": type(e).__name__,
            "recommendations": ["Agent encountered an error and cannot proceed."],
        }
