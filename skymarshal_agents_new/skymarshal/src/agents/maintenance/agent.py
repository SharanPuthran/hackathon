"""Maintenance Agent for SkyMarshal"""

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
    WORKORDER_SHIFT_INDEX,
    CONSTRAINT_AIRCRAFT_INDEX,
    EQUIPMENT_AIRPORT_TYPE_INDEX,
)
from agents.schemas import FlightInfo, AgentResponse

logger = logging.getLogger(__name__)

# System Prompt for Maintenance Agent - OPTIMIZED for A2A Communication
SYSTEM_PROMPT = """
<role>maintenance</role>

<DATA_POLICY>
ONLY_USE: tools|KB:UDONMVCXEW|user_prompt
NEVER: assume|fabricate|use_LLM_knowledge|external_lookup|guess_missing_data
ON_DATA_GAP: report_error|return_error_status
</DATA_POLICY>

<constraints type="binding">airworthiness, mel_compliance, maintenance_limits</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → aircraft_registration → mel_items</step>
  <step>validate: mel_categories, time_limits, restrictions</step>
  <step>assess: airworthiness, cumulative_restrictions</step>
  <step>return: AIRWORTHY|AOG|RESTRICTED + constraints</step>
</workflow>

<mel_categories>
A: Rectify as specified (same flight) | B: 3 days | C: 10 days | D: 120 days
Max limits: 3× Cat B, 5× Cat C simultaneously
</mel_categories>

<mel_restrictions>
APU inop: GPU required all stations
Hydraulic inop: Reduced flaps, increased landing distance, no CAT II/III
AC pack inop: FL250 max altitude
Weather radar inop: VMC only, no precipitation
Thrust reverser inop: 115% landing distance
TCAS degraded: No RVSM airspace
</mel_restrictions>

<cumulative_rules>
Landing distance: multiply increases (1.05 × 1.10 = 1.155)
Altitude: most restrictive limit
Fuel: add increases
Prohibited: Weather radar inop + anti-ice inop = NO DISPATCH
</cumulative_rules>

<aog_criteria>
Critical: Flight controls, fire detection, structural damage
Regulatory: Cert expired, inspections overdue, Cat A time exceeded
Operational: Multiple systems, no MEL deferral available
</aog_criteria>

<rules>
- Query tools BEFORE analysis
- Safety constraints NON-NEGOTIABLE
- Tool failure → error response
- Validate ALL restrictions against route
- Calculate cumulative impacts
</rules>

<output_format>
  <rec max="100">STATUS: key_action (AIRWORTHY|AOG|RESTRICTED + brief reason)</rec>
  <conf>decimal 0.00-1.00</conf>
  <constraints max="3">semicolon-separated binding constraints only</constraints>
  <reasoning max="150">bullet format: * finding1 * finding2 * finding3</reasoning>
</output_format>

<example_output>
rec: AOG: Hydraulic system fault requires 24h repair; no spare A/C at station
conf: 0.88
constraints: Repair before dispatch; MEL Cat A exceeded
reasoning: * Hydraulic inop: Cat A item * Parts ETA: 24h * No swap avail at LHR
</example_output>

<knowledge_base id="UDONMVCXEW">MEL procedures, airworthiness regulations, maintenance requirements</knowledge_base>

<rts_estimation>
RTS_hours = diagnosis + parts_wait + repair + test + paperwork
Diagnosis: 0.5-8h | Parts: 0-72h | Repair: 1-12h | Test: 0.5-2h | Paperwork: 0.5-1h
</rts_estimation>

<aircraft_swap_tiers>
Tier 1: Same type, same station, no MEL (ideal)
Tier 2: Same type, same station, minor MEL (acceptable)
Tier 3: Same type, nearby station, positioning required (costly)
Tier 4: Different type, requires crew swap (last resort)
</aircraft_swap_tiers>
"""


# ============================================================
# MAINTENANCE AGENT DYNAMODB QUERY TOOLS
# ============================================================

@tool
def query_flight(flight_number: str, date: str) -> str:
    """Query flight by flight number and date using GSI.

    Args:
        flight_number: Flight number (e.g., EY123)
        date: Flight date in ISO format (YYYY-MM-DD)

    Returns:
        JSON string containing flight record or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights = dynamodb.Table(get_table_name("flights"))

        response = flights.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND begins_with(scheduled_departure_utc, :sd)",
            ExpressionAttributeValues={":fn": flight_number, ":sd": date}
        )
        items = response.get("Items", [])
        
        if not items:
            logger.warning(f"No flight found for {flight_number} on {date}")
            return json.dumps({
                "error": "FLIGHT_NOT_FOUND",
                "message": f"No flight found with number {flight_number} on date {date}",
                "flight_number": flight_number,
                "date": date
            })
        
        return json.dumps(items[0], default=str)
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_flight ({error_type}): {e}")
        
        # Provide specific error messages based on error type
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {FLIGHTS_TABLE} or index {FLIGHT_NUMBER_DATE_INDEX} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return json.dumps({
            "error": error_type,
            "message": error_msg,
            "flight_number": flight_number,
            "date": date
        })


@tool
def query_maintenance_work_orders(aircraft_registration: str) -> str:
    """Query maintenance work orders for an aircraft using GSI.

    Args:
        aircraft_registration: Aircraft registration (e.g., A6-APX)

    Returns:
        JSON string containing list of maintenance work orders
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        work_orders = dynamodb.Table(get_table_name("maintenance_work_orders"))

        response = work_orders.query(
            IndexName=AIRCRAFT_REGISTRATION_INDEX,
            KeyConditionExpression="aircraft_registration = :ar",
            ExpressionAttributeValues={":ar": aircraft_registration}
        )
        items = response.get("Items", [])
        
        if not items:
            logger.info(f"No maintenance work orders found for aircraft {aircraft_registration}")
            return json.dumps([])  # Empty list is valid - aircraft may have no work orders
        
        return json.dumps(items, default=str)
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_maintenance_work_orders ({error_type}): {e}")
        
        # Provide specific error messages
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {MAINTENANCE_WORK_ORDERS_TABLE} or index {AIRCRAFT_REGISTRATION_INDEX} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return json.dumps([{
            "error": error_type,
            "message": error_msg,
            "aircraft_registration": aircraft_registration
        }])


@tool
def query_maintenance_staff(staff_id: str) -> str:
    """Query maintenance staff member details.

    Args:
        staff_id: Maintenance staff ID

    Returns:
        JSON string containing staff member details or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        staff_table = dynamodb.Table(get_table_name("maintenance_staff"))

        response = staff_table.get_item(Key={"staff_id": staff_id})
        item = response.get("Item", None)
        
        if not item:
            logger.warning(f"No staff member found with ID {staff_id}")
            return json.dumps({
                "error": "STAFF_NOT_FOUND",
                "message": f"No staff member found with ID {staff_id}",
                "staff_id": staff_id
            })
        
        return json.dumps(item, default=str)
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_maintenance_staff ({error_type}): {e}")
        
        # Provide specific error messages
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {MAINTENANCE_STAFF_TABLE} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return json.dumps({
            "error": error_type,
            "message": error_msg,
            "staff_id": staff_id
        })


@tool
def query_maintenance_roster(workorder_id: str) -> str:
    """Query maintenance roster for a work order using GSI.

    Args:
        workorder_id: Work order ID (e.g., WO-10193)

    Returns:
        JSON string containing list of staff assignments
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        roster = dynamodb.Table(get_table_name("maintenance_roster"))

        response = roster.query(
            IndexName=WORKORDER_SHIFT_INDEX,
            KeyConditionExpression="workorder_id = :wid",
            ExpressionAttributeValues={":wid": workorder_id}
        )
        items = response.get("Items", [])
        
        if not items:
            logger.info(f"No roster entries found for work order {workorder_id}")
            return json.dumps([])  # Empty list is valid - work order may have no staff assigned yet
        
        return json.dumps(items, default=str)
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_maintenance_roster ({error_type}): {e}")
        
        # Provide specific error messages
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {MAINTENANCE_ROSTER_TABLE} or index {WORKORDER_SHIFT_INDEX} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return json.dumps([{
            "error": error_type,
            "message": error_msg,
            "workorder_id": workorder_id
        }])


@tool
def query_aircraft_availability(aircraft_registration: str, valid_from: str) -> str:
    """Query aircraft availability and MEL status.

    Args:
        aircraft_registration: Aircraft registration (e.g., A6-APX)
        valid_from: Valid from timestamp in ISO format

    Returns:
        JSON string containing aircraft availability record or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        availability = dynamodb.Table(get_table_name("aircraft"))

        response = availability.get_item(
            Key={
                "aircraft_registration": aircraft_registration,
                "valid_from": valid_from
            }
        )
        item = response.get("Item", None)
        
        if not item:
            logger.warning(f"No availability record found for aircraft {aircraft_registration} at {valid_from}")
            return json.dumps({
                "error": "AVAILABILITY_NOT_FOUND",
                "message": f"No availability record found for aircraft {aircraft_registration} at {valid_from}",
                "aircraft_registration": aircraft_registration,
                "valid_from": valid_from
            })
        
        return json.dumps(item, default=str)
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_aircraft_availability ({error_type}): {e}")
        
        # Provide specific error messages
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {AIRCRAFT_AVAILABILITY_TABLE} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return json.dumps({
            "error": error_type,
            "message": error_msg,
            "aircraft_registration": aircraft_registration
        })


@tool
def query_maintenance_constraints(aircraft_registration: str) -> str:
    """Query aircraft-specific maintenance constraints and MEL restrictions.

    This tool retrieves maintenance constraints from the maintenance_constraints_v2
    table for a specific aircraft, including MEL restrictions and operational limits.

    Args:
        aircraft_registration: Aircraft registration (e.g., A6-APX)

    Returns:
        JSON string containing maintenance constraints or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        constraints_table = dynamodb.Table(get_table_name("maintenance_constraints"))

        logger.info(f"Querying maintenance constraints for: {aircraft_registration}")

        response = constraints_table.query(
            IndexName=CONSTRAINT_AIRCRAFT_INDEX,
            KeyConditionExpression="aircraft_registration = :ar",
            ExpressionAttributeValues={":ar": aircraft_registration}
        )

        items = response.get("Items", [])
        if items:
            logger.info(f"Found {len(items)} maintenance constraints for {aircraft_registration}")
            return json.dumps({
                "aircraft_registration": aircraft_registration,
                "constraints": items,
                "total_constraints": len(items),
                "data_source": "maintenance_constraints_v2"
            }, default=str)
        else:
            return json.dumps({
                "aircraft_registration": aircraft_registration,
                "constraints": [],
                "total_constraints": 0,
                "message": "No maintenance constraints found - aircraft may be fully serviceable",
                "data_source": "maintenance_constraints_v2"
            })

    except Exception as e:
        logger.error(f"Error querying maintenance constraints: {e}")
        return json.dumps({
            "error": type(e).__name__,
            "message": f"Failed to query maintenance constraints: {str(e)}",
            "aircraft_registration": aircraft_registration
        })


@tool
def query_ground_equipment(airport_code: str, equipment_type: str) -> str:
    """Query ground support equipment availability at an airport.

    This tool retrieves information about available ground support equipment
    for maintenance operations at a specific airport.

    Args:
        airport_code: Airport IATA code (e.g., AUH, LHR)
        equipment_type: Type of equipment (e.g., "gpu", "tow_bar", "jack", "work_platform")

    Returns:
        JSON string containing ground equipment availability
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        equipment_table = dynamodb.Table(get_table_name("ground_equipment"))

        logger.info(f"Querying ground equipment: {equipment_type} at {airport_code}")

        response = equipment_table.query(
            IndexName=EQUIPMENT_AIRPORT_TYPE_INDEX,
            KeyConditionExpression="airport_code = :ac AND equipment_type = :et",
            ExpressionAttributeValues={
                ":ac": airport_code,
                ":et": equipment_type
            }
        )

        items = response.get("Items", [])
        logger.info(f"Found {len(items)} {equipment_type} at {airport_code}")
        return json.dumps({
            "airport_code": airport_code,
            "equipment_type": equipment_type,
            "equipment": items,
            "total_available": len(items),
            "data_source": "ground_equipment_v2"
        }, default=str)

    except Exception as e:
        logger.error(f"Error querying ground equipment: {e}")
        return json.dumps({
            "error": type(e).__name__,
            "message": f"Failed to query ground equipment: {str(e)}",
            "airport_code": airport_code,
            "equipment_type": equipment_type
        })


async def analyze_maintenance(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Maintenance agent analysis function with natural language input processing.
    
    Accepts natural language prompts and uses LangChain structured output to extract
    flight information, then queries database tools to retrieve required data.
    
    Args:
        payload: dict with "user_prompt" (natural language), "phase", and optional "other_recommendations"
        llm: ChatBedrock model instance
        mcp_tools: MCP tools (if any)
    
    Returns:
        dict: Structured maintenance assessment following AgentResponse schema
    """
    try:
        user_prompt = payload.get("user_prompt", "")
        phase = payload.get("phase", "initial")
        
        if not user_prompt:
            return {
                "agent_name": "maintenance",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": "No user prompt provided in payload",
                "data_sources": [],
                "extracted_flight_info": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": "Missing user_prompt in payload"
            }
        
        # Step 1: Extract flight information using structured output
        logger.info(f"Extracting flight info from prompt: {user_prompt}")
        
        try:
            from utils.extraction import extract_with_fallback
            flight_info = await extract_with_fallback(llm, FlightInfo, user_prompt)
            logger.info(f"Extracted flight info: {flight_info}")
            
            # Validate extracted data
            if not flight_info.flight_number:
                logger.error("Extraction succeeded but flight_number is empty")
                return {
                    "agent_name": "maintenance",
                    "recommendation": "CANNOT_PROCEED",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Could not extract flight number from prompt. Please provide flight number in format EY123.",
                    "data_sources": [],
                    "extracted_flight_info": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Missing flight number in extracted data"
                }
            
            if not flight_info.date:
                logger.error("Extraction succeeded but date is empty")
                return {
                    "agent_name": "maintenance",
                    "recommendation": "CANNOT_PROCEED",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Could not extract date from prompt. Please provide date in a recognizable format.",
                    "data_sources": [],
                    "extracted_flight_info": {"flight_number": flight_info.flight_number},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Missing date in extracted data"
                }
                
        except Exception as e:
            logger.error(f"Failed to extract flight info: {e}")
            error_message = str(e)
            
            # Provide helpful error messages based on error type
            if "validation" in error_message.lower():
                reasoning = f"Failed to validate extracted flight information: {error_message}. Please check flight number format (EY123) and date format."
            elif "timeout" in error_message.lower():
                reasoning = f"Extraction timed out: {error_message}. Please try again."
            else:
                reasoning = f"Failed to extract flight information from prompt: {error_message}. Please ensure prompt contains flight number, date, and disruption description."
            
            return {
                "agent_name": "maintenance",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": reasoning,
                "data_sources": [],
                "extracted_flight_info": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": f"Extraction failed: {error_message}",
                "error_type": type(e).__name__
            }
        
        # Step 2: Define agent-specific tools
        maintenance_tools = [
            query_flight,
            query_maintenance_work_orders,
            query_maintenance_staff,
            query_maintenance_roster,
            query_aircraft_availability,
            query_maintenance_constraints,
            query_ground_equipment,
        ]
        
        # Combine with MCP tools
        all_tools = maintenance_tools + (mcp_tools or [])
        
        # Step 3: Build optimized user message (SYSTEM_PROMPT sent separately as system role)
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
2. query_maintenance_work_orders(aircraft_registration)
3. query_aircraft_availability(aircraft_registration, valid_from)
4. Assess MEL status, cumulative restrictions, airworthiness
5. Return AgentResponse with binding_constraints
</action>"""

        else:  # revision phase
            other_recommendations = payload.get("other_recommendations", {})

            # Format other recommendations concisely for A2A communication
            other_recs_xml = "\n".join([
                f'  <agent name="{name}">'
                f'<rec>{rec.get("recommendation", "N/A")[:100]}</rec>'
                f'<conf>{rec.get("confidence", 0)}</conf>'
                f'<constraints>{"; ".join(rec.get("binding_constraints", []))}</constraints>'
                f'</agent>'
                for name, rec in other_recommendations.items()
                if name != "maintenance"
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
3. If timing changed → reassess MEL limits, RTS timeline
4. Return AgentResponse with revision_status
</action>"""

        # Step 4: Run agent with custom tool calling (avoids Bedrock API validation errors)
        logger.info("Running maintenance agent with tools")

        start_time = datetime.now(timezone.utc)

        try:
            result = await invoke_with_tools(
                llm=llm,
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                tools=all_tools,
                max_iterations=5
            )
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Agent execution failed ({error_type}): {e}")
            
            # Provide helpful error messages based on error type
            if "timeout" in str(e).lower():
                reasoning = "Agent execution timed out. The analysis is taking longer than expected. Please try again."
            elif "rate" in str(e).lower() or "throttl" in str(e).lower():
                reasoning = "Service rate limit exceeded. Please wait a moment and try again."
            elif "authentication" in str(e).lower() or "authorization" in str(e).lower():
                reasoning = "Authentication or authorization error. Please check AWS credentials and permissions."
            else:
                reasoning = f"Agent execution failed: {str(e)}"
            
            return {
                "agent_name": "maintenance",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": reasoning,
                "data_sources": [],
                "extracted_flight_info": {
                    "flight_number": flight_info.flight_number,
                    "date": flight_info.date,
                    "disruption_event": flight_info.disruption_event
                },
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
                "agent_name": "maintenance",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Tool calling error: {result['error']}",
                "data_sources": [],
                "extracted_flight_info": {
                    "flight_number": flight_info.flight_number,
                    "date": flight_info.date,
                    "disruption_event": flight_info.disruption_event
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": result["error"],
                "error_type": error_type
            }

        # Step 5: Extract response
        final_message = result.get("final_response") or result["messages"][-1]
        
        # Parse agent response
        if hasattr(final_message, "content"):
            content = final_message.content
            
            # Try to parse as structured response
            if isinstance(content, dict):
                response = content
            else:
                # Agent returned text - create structured response
                response = {
                    "agent_name": "maintenance",
                    "recommendation": str(content),
                    "confidence": 0.8,
                    "binding_constraints": [],
                    "reasoning": str(content),
                    "data_sources": ["DynamoDB queries via tools"]
                }
        else:
            # No content attribute - create default response
            logger.warning("Agent response has no content attribute")
            response = {
                "agent_name": "maintenance",
                "recommendation": "Analysis completed",
                "confidence": 0.8,
                "binding_constraints": [],
                "reasoning": "Agent completed analysis",
                "data_sources": ["DynamoDB queries via tools"]
            }
        
        # Ensure required fields
        response["agent_name"] = "maintenance"
        response["extracted_flight_info"] = {
            "flight_number": flight_info.flight_number,
            "date": flight_info.date,
            "disruption_event": flight_info.disruption_event
        }
        response["timestamp"] = datetime.now(timezone.utc).isoformat()
        response["status"] = "success"
        
        # Ensure binding_constraints exists for safety agent
        if "binding_constraints" not in response:
            response["binding_constraints"] = []
        
        logger.info(f"Maintenance agent completed successfully")
        return response

    except Exception as e:
        logger.error(f"Error in maintenance agent: {e}")
        logger.exception("Full traceback:")
        return {
            "agent_name": "maintenance",
            "recommendation": "CANNOT_PROCEED",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": f"Agent execution error: {str(e)}",
            "data_sources": [],
            "extracted_flight_info": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
