"""Cargo Agent for SkyMarshal"""

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
    CARGO_FLIGHT_ASSIGNMENTS_TABLE,
    CARGO_SHIPMENTS_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_LOADING_INDEX,
    SHIPMENT_INDEX,
)
from agents.schemas import FlightInfo, AgentResponse, CargoOutput

logger = logging.getLogger(__name__)

# ============================================================================
# DynamoDB Query Tools for Cargo Agent
# ============================================================================
# 
# The Cargo Agent has access to the following tables:
# - flights: Flight schedule and operational data
# - CargoFlightAssignments: Cargo assignments to flights
# - CargoShipments: Detailed cargo shipment information
#
# These tools use GSIs for efficient querying:
# - flight-number-date-index: Query flights by flight number and date
# - flight-loading-index: Query cargo assignments by flight and loading status
# - shipment-index: Query cargo assignments by shipment ID
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
def query_cargo_manifest(flight_id: str) -> str:
    """Query cargo manifest for a flight using GSI.
    
    This tool retrieves all cargo assignments for a specific flight using the
    flight-loading-index GSI. Returns cargo assignments with loading status.
    
    Args:
        flight_id: Unique flight identifier (e.g., EY123-20260120)
    
    Returns:
        JSON string containing list of cargo assignment records
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        cargo_table = dynamodb.Table(CARGO_FLIGHT_ASSIGNMENTS_TABLE)
        
        logger.info(f"Querying cargo manifest for flight: {flight_id}")
        
        response = cargo_table.query(
            IndexName=FLIGHT_LOADING_INDEX,
            KeyConditionExpression="flight_id = :fid",
            ExpressionAttributeValues={
                ":fid": flight_id,
            },
        )
        
        items = response.get("Items", [])
        logger.info(f"Found {len(items)} cargo assignments for flight {flight_id}")
        return json.dumps(items, default=str)
        
    except Exception as e:
        logger.error(f"Error querying cargo manifest: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_shipment_details(shipment_id: str) -> str:
    """Query detailed shipment information by shipment ID.
    
    This tool retrieves complete shipment details from the CargoShipments table
    including AWB information, commodity type, temperature requirements, and value.
    
    Args:
        shipment_id: Unique shipment identifier
    
    Returns:
        JSON string containing shipment record or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        shipments_table = dynamodb.Table(CARGO_SHIPMENTS_TABLE)
        
        logger.info(f"Querying shipment details: {shipment_id}")
        
        response = shipments_table.get_item(
            Key={"shipment_id": shipment_id}
        )
        
        item = response.get("Item")
        if item:
            logger.info(f"Found shipment: {shipment_id}")
            return json.dumps(item, default=str)
        else:
            logger.warning(f"Shipment not found: {shipment_id}")
            return json.dumps({"error": "SHIPMENT_NOT_FOUND", "message": f"Shipment {shipment_id} not found"})
            
    except Exception as e:
        logger.error(f"Error querying shipment details: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@tool
def query_shipment_by_awb(awb_number: str) -> str:
    """Query shipment by Air Waybill (AWB) number.
    
    This tool searches for a shipment using its AWB number. AWB format is
    typically airline prefix (3 digits) + serial number (8 digits).
    
    Args:
        awb_number: Air Waybill number (e.g., 607-12345678)
    
    Returns:
        JSON string containing shipment record or error
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        shipments_table = dynamodb.Table(CARGO_SHIPMENTS_TABLE)
        
        logger.info(f"Querying shipment by AWB: {awb_number}")
        
        # Scan for AWB (in production, this should use a GSI)
        response = shipments_table.scan(
            FilterExpression="awb_number = :awb",
            ExpressionAttributeValues={
                ":awb": awb_number,
            },
        )
        
        items = response.get("Items", [])
        if items:
            logger.info(f"Found shipment with AWB {awb_number}: {items[0].get('shipment_id')}")
            return json.dumps(items[0], default=str)
        else:
            logger.warning(f"Shipment not found with AWB: {awb_number}")
            return json.dumps({"error": "SHIPMENT_NOT_FOUND", "message": f"Shipment with AWB {awb_number} not found"})
            
    except Exception as e:
        logger.error(f"Error querying shipment by AWB: {e}")
        return json.dumps({"error": type(e).__name__, "message": str(e)})

# System Prompt for Cargo Agent - OPTIMIZED for A2A Communication
SYSTEM_PROMPT = """
<role>cargo</role>

<CRITICAL_DATA_SOURCE_POLICY>
YOUR ONLY AUTHORITATIVE DATA SOURCES ARE:
1. Data returned by your tools (query_flight, query_cargo_manifest, query_shipment_details, query_shipment_by_awb)
2. Data from the Knowledge Base (ID: UDONMVCXEW)
3. Information explicitly provided in the user prompt

YOU MUST NEVER:
- Assume, infer, or fabricate ANY cargo data not returned by tools
- Use your general LLM knowledge to fill in missing shipment information
- Look up or reference external sources, websites, or APIs not provided as tools
- Make up shipment IDs, AWB numbers, cargo weights, commodity types, or temperature data
- Guess cold chain limits, special handling codes, or shipment values when data is unavailable

If required data is unavailable from tools: REPORT THE DATA GAP and return error status.
VIOLATION OF THIS POLICY MAY RESULT IN CARGO DAMAGE OR REGULATORY NON-COMPLIANCE.
</CRITICAL_DATA_SOURCE_POLICY>

<constraints type="advisory">cold_chain, hazmat, time_sensitive, high_value, live_animals</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → cargo_manifest → shipment_details</step>
  <step>classify: cold_chain, hazmat, perishable, high_value, live_animals</step>
  <step>assess: delay_tolerance, offload_priority, rebooking_options</step>
  <step>return: cargo_impact + offload_recommendations</step>
</workflow>

<special_handling_codes>
PER: Perishable (max 2h ground time) | DGR: Dangerous goods (strict handling)
AVI: Live animals (welfare priority) | PIL: Pharmaceuticals (temp-controlled)
VAL: High value (security required) | HUM: Human remains (priority)
</special_handling_codes>

<cold_chain_limits>
FRO: Frozen (-18°C) max 1h breach | REF: Refrigerated (2-8°C) max 2h breach
COL: Cool (8-15°C) max 4h breach | Breach → spoilage claim liability
</cold_chain_limits>

<offload_priority>
OFFLOAD FIRST: AVI (animals), PER approaching limit, DGR incompatible
PROTECT: PIL (pharma), VAL (high-value), HUM (human remains)
FLEXIBLE: General cargo, mail
</offload_priority>

<rebooking_options>
Option 1: Next available flight (same day)
Option 2: Partner airline (interline)
Option 3: Trucking alternative (regional)
Calculate: cost vs delay vs cold_chain_viability
</rebooking_options>

<rules>
- Query cargo manifest BEFORE assessment
- Identify special handling requirements first
- Calculate delay tolerance per shipment type
- Never offload live animals without welfare review
- Safety constraints override cargo efficiency
</rules>

<output_format>
  <rec max="100">CARGO_STATUS: risk_level + critical items + offload/protect action</rec>
  <conf>decimal 0.00-1.00</conf>
  <reasoning max="150">bullet format: * critical_cargo * time_limit * action</reasoning>
</output_format>

<example_output>
rec: CRITICAL: 3 cold-chain shipments at risk (2h limit); offload AVI, protect PIL pharma
conf: 0.90
reasoning: * 3 PER items: 2h limit * 1 AVI: welfare priority * 2 PIL: temp-controlled
</example_output>

<knowledge_base id="UDONMVCXEW">IATA DGR, cold chain SOP, live animal regulations</knowledge_base>
"""


# NOTE: Verbose documentation moved to Knowledge Base (ID: UDONMVCXEW)
async def analyze_cargo(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Cargo agent analysis function with structured output and DynamoDB tools.
    
    This agent:
    1. Uses LangChain structured output to extract flight info from natural language
    2. Defines its own DynamoDB query tools for authorized tables
    3. Queries cargo manifest and shipment details
    4. Analyzes cargo impact including cold chain, perishables, and high-value cargo
    
    Args:
        payload: Request payload containing:
            - user_prompt: Natural language prompt with flight and disruption info
            - phase: "initial" or "revision"
            - other_recommendations: Other agents' recommendations (revision phase only)
        llm: Bedrock model instance (ChatBedrock)
        mcp_tools: MCP tools for additional capabilities
    
    Returns:
        Structured cargo assessment with cargo risk score, financial exposure,
        and recommendations
    """
    try:
        user_prompt = payload.get("user_prompt", payload.get("prompt", ""))
        phase = payload.get("phase", "initial")
        
        if not user_prompt:
            return {
                "agent": "cargo",
                "category": "business",
                "assessment": "CANNOT_PROCEED",
                "status": "error",
                "failure_reason": "No user prompt provided",
                "recommendations": ["Please provide a disruption description with flight number and date."],
            }
        
        # Step 1: Extract flight information using structured output
        logger.info("Extracting flight information from natural language prompt")
        try:
            from utils.extraction import extract_with_fallback
            # Note: cargo agent uses sync invoke, need to make it async
            flight_info = await extract_with_fallback(llm, FlightInfo, user_prompt)
            logger.info(f"Extracted flight info: {flight_info.flight_number} on {flight_info.date}")
        except Exception as e:
            logger.error(f"Failed to extract flight information: {e}")
            return {
                "agent": "cargo",
                "category": "business",
                "assessment": "CANNOT_PROCEED",
                "status": "error",
                "failure_reason": f"Could not extract flight information from prompt: {str(e)}",
                "missing_data": ["flight_number", "date"],
                "recommendations": [
                    "Please provide flight number (e.g., EY123) and date in your prompt.",
                    "Example: 'Flight EY123 on January 20th had a mechanical failure'"
                ],
                "extracted_flight_info": None,
            }
        
        # Step 2: Define cargo-specific DynamoDB tools
        cargo_tools = [
            query_flight,
            query_cargo_manifest,
            query_shipment_details,
            query_shipment_by_awb,
        ]
        
        # Step 3: Build optimized user message (SYSTEM_PROMPT sent separately as system role)
        if phase == "revision":
            other_recs = payload.get("other_recommendations", {})

            # Format other recommendations concisely for A2A communication
            other_recs_xml = "\n".join([
                f'  <agent name="{name}">'
                f'<rec>{rec.get("recommendation", "N/A")[:100]}</rec>'
                f'<conf>{rec.get("confidence", 0)}</conf>'
                f'<constraints>{"; ".join(rec.get("binding_constraints", []))}</constraints>'
                f'</agent>'
                for name, rec in other_recs.items()
                if name != "cargo"
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
3. If timing changed → reassess cold chain viability
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
2. query_cargo_manifest(flight_id)
3. query_shipment_details(shipment_id) for special handling
4. Assess cold chain, perishables, high-value cargo
5. Return AgentResponse with cargo_at_risk, offload_list
</action>"""

        # Step 4: Run agent with custom tool calling (avoids Bedrock API validation errors)
        logger.info(f"Running cargo agent in {phase} phase")
        all_tools = mcp_tools + cargo_tools
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
                "agent": "cargo",
                "category": "business",
                "assessment": "CANNOT_PROCEED",
                "status": "error",
                "failure_reason": f"Tool calling error: {result['error']}",
                "error": result["error"],
                "recommendations": ["Agent encountered an error and cannot proceed."],
            }
        
        # Step 5: Extract structured output
        final_message = result.get("final_response")
        
        if hasattr(final_message, "content") and isinstance(final_message.content, dict):
            structured_result = final_message.content
        elif hasattr(final_message, "tool_calls") and final_message.tool_calls:
            structured_result = final_message.tool_calls[0]["args"]
        else:
            structured_result = {
                "agent": "cargo",
                "category": "business",
                "result": str(final_message.content),
                "status": "success",
            }
        
        # Step 7: Ensure required fields
        structured_result["agent"] = "cargo"
        structured_result["category"] = "business"
        # Only set status to success if not already set by agent
        if "status" not in structured_result:
            structured_result["status"] = "success"
        structured_result["extracted_flight_info"] = flight_info.model_dump()
        
        logger.info("Cargo agent analysis completed successfully")
        return structured_result
        
    except Exception as e:
        logger.error(f"Error in cargo agent: {e}")
        logger.exception("Full traceback:")
        return {
            "agent": "cargo",
            "category": "business",
            "assessment": "CANNOT_PROCEED",
            "status": "error",
            "failure_reason": f"Agent execution error: {str(e)}",
            "error": str(e),
            "error_type": type(e).__name__,
            "recommendations": ["Agent encountered an error and cannot proceed."],
        }
