"""Finance Agent for SkyMarshal"""

import logging
import json
from typing import Any, Optional, Dict, List
import boto3
from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from utils.tool_calling import invoke_with_tools
from database.table_config import get_table_name
from database.constants import (
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_ID_INDEX,
    FLIGHT_LOADING_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
    CATEGORY_INDEX,
    SCENARIO_TYPE_INDEX,
    REGULATION_INDEX,
    FIRST_LEG_FLIGHT_INDEX,
)
from agents.schemas import FlightInfo, AgentResponse, FinanceOutput

logger = logging.getLogger(__name__)

# ============================================================================
# DynamoDB Query Tools for Finance Agent
# ============================================================================
# 
# The Finance Agent has access to the following tables:
# - flights: Flight schedule and operational data
# - bookings: Passenger bookings and revenue data
# - CargoFlightAssignments: Cargo assignments and revenue
# - MaintenanceWorkOrders: Maintenance costs and schedules
#
# These tools use GSIs for efficient querying:
# - flight-number-date-index: Query flights by flight number and date
# - flight-id-index: Query bookings by flight ID
# - flight-loading-index: Query cargo assignments by flight
# - aircraft-registration-index: Query maintenance by aircraft
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
        flights_table = dynamodb.Table(get_table_name("flights"))
        
        logger.info(f"Querying flight: {flight_number} on {date}")
        
        response = flights_table.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND begins_with(scheduled_departure_utc, :sd)",
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
def query_passenger_bookings(flight_id: str) -> str:
    """Query passengers for a flight using V2 passengers table with first-leg-flight-index GSI.

    This tool retrieves all passengers for a specific flight using the
    first-leg-flight-index GSI on passengers_v2. Returns passenger records with
    fare class, PNR, and frequent flyer information for revenue calculations.

    Args:
        flight_id: Unique flight identifier (e.g., "FLT-2001")

    Returns:
        JSON string containing list of passenger records
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        # Use passengers_v2 table with first-leg-flight-index GSI
        # V1 bookings table uses numeric flight_id, V2 uses string format
        passengers_table = dynamodb.Table(get_table_name("passengers"))

        logger.info(f"Querying passengers for flight: {flight_id}")

        response = passengers_table.query(
            IndexName=FIRST_LEG_FLIGHT_INDEX,
            KeyConditionExpression="first_leg_flight_id = :fid",
            ExpressionAttributeValues={
                ":fid": flight_id,
            },
        )

        items = response.get("Items", [])
        logger.info(f"Found {len(items)} passengers for flight {flight_id}")
        return json.dumps(items, default=str)

    except Exception as e:
        logger.error(f"Error querying passengers: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_cargo_revenue(flight_id: str) -> str:
    """Query cargo shipments for revenue calculation using V2 table with first-leg-flight-index GSI.

    This tool retrieves all cargo shipments for a specific flight using the
    first-leg-flight-index GSI on cargo_shipments_v2. Returns shipment records
    with weight, value, and special handling data for revenue calculations.

    Args:
        flight_id: Unique flight identifier (e.g., "FLT-2001")

    Returns:
        JSON string containing list of cargo shipment records
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        # Use cargo_shipments_v2 table with first-leg-flight-index GSI
        # V1 CargoFlightAssignments uses numeric flight_id, V2 uses string format
        shipments_table = dynamodb.Table(get_table_name("cargo_shipments"))

        logger.info(f"Querying cargo revenue for flight: {flight_id}")

        response = shipments_table.query(
            IndexName=FIRST_LEG_FLIGHT_INDEX,
            KeyConditionExpression="first_leg_flight_id = :fid",
            ExpressionAttributeValues={
                ":fid": flight_id,
            },
        )

        items = response.get("Items", [])
        logger.info(f"Found {len(items)} cargo shipments for flight {flight_id}")
        return json.dumps(items, default=str)

    except Exception as e:
        logger.error(f"Error querying cargo revenue: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_maintenance_costs(aircraft_registration: str) -> str:
    """Query maintenance work orders for cost analysis using GSI.
    
    This tool retrieves maintenance work orders for a specific aircraft using the
    aircraft-registration-index GSI. Returns work orders with cost and schedule data.
    
    Args:
        aircraft_registration: Aircraft tail number (e.g., A6-APX)
    
    Returns:
        JSON string containing list of maintenance work order records
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        maintenance_table = dynamodb.Table(get_table_name("maintenance_work_orders"))
        
        logger.info(f"Querying maintenance costs for aircraft: {aircraft_registration}")
        
        response = maintenance_table.query(
            IndexName=AIRCRAFT_REGISTRATION_INDEX,
            KeyConditionExpression="aircraftRegistration = :ar",
            ExpressionAttributeValues={
                ":ar": aircraft_registration,
            },
        )
        
        items = response.get("Items", [])
        logger.info(f"Found {len(items)} maintenance work orders for aircraft {aircraft_registration}")
        return json.dumps(items, default=str)
        
    except Exception as e:
        logger.error(f"Error querying maintenance costs: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def get_current_datetime_tool() -> str:
    """Returns current UTC datetime for date resolution.

    Use this tool when you need to resolve relative dates like 'yesterday',
    'today', or 'tomorrow', or when you need the current date/time for context.

    Returns:
        str: Current UTC datetime in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)

    Example:
        >>> current_time = get_current_datetime_tool()
        >>> print(current_time)
        '2026-01-30T14:30:00Z'
    """
    return datetime.now(timezone.utc).isoformat()


@tool
def query_financial_parameters(parameter_type: str) -> str:
    """Query financial parameters for cost calculations.

    This tool retrieves financial parameters such as crew overtime rates,
    fuel costs, compensation rates, and other cost factors from the
    financial_parameters_v2 table.

    Args:
        parameter_type: Type of parameter (e.g., "crew_costs", "fuel_rates",
                       "compensation_rates", "hotel_rates", "meal_rates")

    Returns:
        JSON string containing financial parameters or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        params_table = dynamodb.Table(get_table_name("financial_parameters"))

        logger.info(f"Querying financial parameters: {parameter_type}")

        # Table PK is parameter_id, not parameter_type
        # Use scan with filter since there's no GSI for parameter_type
        response = params_table.scan(
            FilterExpression="parameter_type = :pt",
            ExpressionAttributeValues={":pt": parameter_type}
        )

        items = response.get("Items", [])
        if items:
            logger.info(f"Found financial parameters for {parameter_type}")
            return json.dumps(items[0], default=str)
        else:
            logger.warning(f"Financial parameters not found for {parameter_type}")
            return json.dumps({
                "error": "PARAMETERS_NOT_FOUND",
                "message": f"Financial parameters for {parameter_type} not found",
                "parameter_type": parameter_type,
                "data_source": "financial_parameters_v2"
            })

    except Exception as e:
        logger.error(f"Error querying financial parameters: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_recovery_cost_matrix(scenario_type: str, aircraft_type: str) -> str:
    """Query cost matrix for recovery scenarios.

    This tool retrieves cost data for different recovery scenarios
    (delay, cancel, swap) by aircraft type from recovery_cost_matrix_v2.

    Args:
        scenario_type: Recovery scenario type (e.g., "DELAY", "CANCEL", "SWAP")
        aircraft_type: Aircraft type code (e.g., "B787", "A380", "A350")

    Returns:
        JSON string containing cost matrix data or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        cost_table = dynamodb.Table(get_table_name("recovery_cost_matrix"))

        logger.info(f"Querying recovery cost matrix: {scenario_type} for {aircraft_type}")

        # Table PK is matrix_id, use scenario-type-index GSI with filter on aircraft_type
        response = cost_table.query(
            IndexName=SCENARIO_TYPE_INDEX,
            KeyConditionExpression="scenario_type = :st",
            FilterExpression="aircraft_type = :at",
            ExpressionAttributeValues={
                ":st": scenario_type,
                ":at": aircraft_type
            }
        )

        items = response.get("Items", [])
        if items:
            logger.info(f"Found cost matrix for {scenario_type}/{aircraft_type}")
            return json.dumps(items[0], default=str)
        else:
            logger.warning(f"Cost matrix not found for {scenario_type}/{aircraft_type}")
            return json.dumps({
                "error": "COST_MATRIX_NOT_FOUND",
                "message": f"No cost matrix for scenario {scenario_type} and aircraft {aircraft_type}",
                "data_source": "recovery_cost_matrix_v2"
            })

    except Exception as e:
        logger.error(f"Error querying recovery cost matrix: {e}")
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
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        rules_table = dynamodb.Table(get_table_name("compensation_rules"))

        logger.info(f"Querying compensation rules: {regulation} / {delay_category}")

        # Use regulation-index GSI with filter on delay_category
        # Table PK is rule_id, so we must use GSI for regulation lookup
        response = rules_table.query(
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
            logger.info(f"Found compensation rules for {regulation}/{delay_category}")
            return json.dumps(items[0], default=str)
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


# System Prompt for Finance Agent - OPTIMIZED for A2A Communication
SYSTEM_PROMPT = """
<role>finance</role>

<DATA_POLICY>
ONLY_USE: tools|KB:UDONMVCXEW|user_prompt
NEVER: assume|fabricate|use_LLM_knowledge|external_lookup|guess_missing_data
ON_DATA_GAP: report_error|return_error_status
</DATA_POLICY>

<constraints type="advisory">cost_optimization, revenue_protection, scenario_comparison</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → bookings → cargo_assignments</step>
  <step>calculate: passenger_revenue, cargo_revenue, crew_costs, maintenance_costs</step>
  <step>compare: delay_cost vs cancel_cost vs aircraft_swap_cost</step>
  <step>return: cost_breakdown + scenario_comparison + recommended_scenario</step>
</workflow>

<cost_components>
Passenger: Compensation + meals + hotels + rebooking
Crew: Overtime ($150 captain, $100 FO, $50 cabin per hour) + positioning + hotels
Aircraft: Fuel burn ($1.50/kg) + parking + maintenance window impact
Cargo: Rebooking + spoilage claims + cold chain breach
Reputation: NPS impact × customer lifetime value
</cost_components>

<cost_formulas>
delay_cost = (comp_per_hour × pax × hours) + crew_overtime + fuel_burn
cancel_cost = full_refunds + compensation_eu261 + rebooking_cost + crew_repos
swap_cost = positioning_fuel + crew_ferry + schedule_disruption
</cost_formulas>

<compensation_rates>
EU261: €250 (<1500km, 2-3h) | €400 (1500-3500km, 3-4h) | €600 (>3500km, >4h)
DOT: 200% ticket (1-2h) | 400% ticket (>2h)
Meals: €15/pax (2-4h) | €30/pax (>4h)
Hotels: €120/pax (overnight delay)
Crew positioning: $100 (local) | $500 (domestic) | $1000 (international)
</compensation_rates>

<scenario_comparison>
Always compare minimum 3 scenarios: DELAY | CANCEL | SWAP
Include: Direct costs + indirect costs + opportunity costs + reputation
Rank by: Net financial impact (lowest total cost)
Weight: Safety (40%), Cost (25%), Pax (20%), Network (10%), Reputation (5%)
</scenario_comparison>

<rules>
- Query revenue data BEFORE cost calculation
- Calculate ALL cost components for each scenario
- Compare minimum 3 scenarios always
- Include reputation/NPS in total cost
- Safety constraints override cost optimization
</rules>

<output_format>
  <rec max="100">BEST_SCENARIO: scenario_name + total_cost + vs alternatives</rec>
  <conf>decimal 0.00-1.00</conf>
  <reasoning max="150">bullet format: * delay_cost * cancel_cost * swap_cost * winner</reasoning>
</output_format>

<example_output>
rec: DELAY_BEST: €210K total (vs €450K cancel, €320K swap); 3h delay optimal
conf: 0.88
reasoning: * Delay: €210K (comp+crew) * Cancel: €450K (refunds+repos) * Winner: DELAY
</example_output>

<knowledge_base id="UDONMVCXEW">Cost models, compensation rates, fuel costs, revenue data</knowledge_base>
"""


# NOTE: Verbose documentation moved to Knowledge Base (ID: UDONMVCXEW)
async def analyze_finance(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Finance agent analysis function with structured output and DynamoDB tools.
    
    This agent:
    1. Extracts flight information from natural language using structured output
    2. Queries DynamoDB for financial data (bookings, cargo, maintenance)
    3. Calculates cost impacts, compensation, and revenue implications
    4. Returns structured financial assessment
    
    Args:
        payload: Request payload with 'user_prompt' field containing natural language
        llm: Bedrock model instance (ChatBedrock)
        mcp_tools: MCP tools from gateway
    
    Returns:
        dict: Structured finance assessment using FinanceOutput schema
    """
    try:
        # Define DynamoDB query tools for Finance Agent
        db_tools = [
            query_flight,
            query_passenger_bookings,
            query_cargo_revenue,
            query_maintenance_costs,
            get_current_datetime_tool,
            query_financial_parameters,
            query_recovery_cost_matrix,
            query_compensation_rules,
        ]
        
        # Get user prompt
        user_prompt = payload.get("user_prompt", payload.get("prompt", ""))
        phase = payload.get("phase", "initial")
        other_recommendations = payload.get("other_recommendations", {})

        # Extract flight information using structured output
        logger.info("Extracting flight information from natural language prompt")
        try:
            from utils.extraction import extract_with_fallback
            flight_info = await extract_with_fallback(llm, FlightInfo, user_prompt)
            logger.info(f"Extracted flight info: {flight_info.flight_number} on {flight_info.date}")
        except Exception as e:
            logger.error(f"Failed to extract flight information: {e}")
            return {
                "agent": "finance",
                "category": "business",
                "assessment": "CANNOT_PROCEED",
                "status": "error",
                "failure_reason": f"Could not extract flight information: {str(e)}",
                "recommendations": ["Please provide flight number and date in your prompt."],
            }

        # Build optimized user message (SYSTEM_PROMPT sent separately as system role)
        if phase == "revision":
            # Format other recommendations concisely for A2A communication
            other_recs_xml = "\n".join([
                f'  <agent name="{name}">'
                f'<rec>{rec.get("recommendation", "N/A")[:100]}</rec>'
                f'<conf>{rec.get("confidence", 0)}</conf>'
                f'<constraints>{"; ".join(rec.get("binding_constraints", []))}</constraints>'
                f'</agent>'
                for name, rec in other_recommendations.items()
                if name != "finance"
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
3. If constraints changed → recalculate cost scenarios
4. Return AgentResponse with revision_status
</action>"""
        else:
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
2. query_passenger_bookings(flight_id)
3. query_cargo_revenue(flight_id)
4. query_maintenance_costs(aircraft_registration)
5. Calculate: delay_cost, cancel_cost, swap_cost
6. Compare minimum 3 scenarios, rank by net impact
7. Return AgentResponse with cost_breakdown, scenario_comparison
</action>"""

        # Run agent with custom tool calling (avoids Bedrock API validation errors)
        logger.info(f"Running finance agent in {phase} phase")
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
                "agent": "finance",
                "category": "business",
                "assessment": "CANNOT_PROCEED",
                "status": "error",
                "failure_reason": f"Tool calling error: {result['error']}",
                "error": result["error"],
                "recommendations": ["Agent encountered an error and cannot proceed."],
            }
        
        # Extract structured output
        final_message = result.get("final_response")
        
        # Check if we got structured output
        if hasattr(final_message, "content") and isinstance(
            final_message.content, dict
        ):
            structured_result = final_message.content
        elif hasattr(final_message, "tool_calls") and final_message.tool_calls:
            # Extract from tool call if that's how it was returned
            structured_result = final_message.tool_calls[0]["args"]
        else:
            # Fallback: parse content as dict
            structured_result = {
                "agent": "finance",
                "category": "business",
                "result": str(final_message.content),
                "status": "success",
            }
        
        # Ensure required fields are present
        if "agent" not in structured_result:
            structured_result["agent"] = "finance"
        if "category" not in structured_result:
            structured_result["category"] = "business"
        if "status" not in structured_result:
            structured_result["status"] = "success"
        
        # Add extracted flight info
        structured_result["extracted_flight_info"] = {
            "flight_number": flight_info.flight_number,
            "date": flight_info.date,
            "disruption_event": flight_info.disruption_event
        }
        
        logger.info(f"Finance agent completed successfully for phase: {phase}")
        return structured_result
        
    except Exception as e:
        logger.error(f"Error in finance agent: {e}")
        logger.exception("Full traceback:")
        return {
            "agent": "finance",
            "category": "business",
            "assessment": "CANNOT_PROCEED",
            "status": "error",
            "failure_reason": f"Agent execution error: {str(e)}",
            "error": str(e),
            "error_type": type(e).__name__,
            "recommendations": [
                "Agent encountered an error and cannot proceed.",
                "Check logs for detailed error information.",
                "Verify database connectivity and tool availability."
            ],
            "missing_data": ["Unable to complete analysis due to error"],
            "attempted_tools": ["agent execution failed before tool invocation"],
        }
