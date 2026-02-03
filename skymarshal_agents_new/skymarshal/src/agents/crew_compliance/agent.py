"""Crew Compliance Agent for SkyMarshal"""

import json
import logging
from typing import Any
import boto3
from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from utils.tool_calling import invoke_with_tools
from database.constants import (
    FLIGHTS_TABLE,
    CREW_ROSTER_TABLE,
    CREW_MEMBERS_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_POSITION_INDEX,
    CREW_DUTY_DATE_INDEX,
)
from agents.schemas import FlightInfo, AgentResponse

logger = logging.getLogger(__name__)

# System Prompt for Crew Compliance Agent - OPTIMIZED for A2A Communication
SYSTEM_PROMPT = """
<role>crew_compliance</role>

<CRITICAL_DATA_SOURCE_POLICY>
YOUR ONLY AUTHORITATIVE DATA SOURCES ARE:
1. Data returned by your tools (query_flight, query_crew_roster, query_crew_members)
2. Data from the Knowledge Base (ID: UDONMVCXEW)
3. Information explicitly provided in the user prompt

YOU MUST NEVER:
- Assume, infer, or fabricate ANY crew data not returned by tools
- Use your general LLM knowledge to fill in missing FDP, rest, or qualification data
- Look up or reference external sources, websites, or APIs not provided as tools
- Make up crew names, duty times, rest periods, qualifications, or medical certificate statuses
- Guess FDP limits, rest requirements, or crew availability when data is unavailable

If required data is unavailable from tools: REPORT THE DATA GAP and return error status.
VIOLATION OF THIS POLICY COMPROMISES FLIGHT SAFETY AND REGULATORY COMPLIANCE.
</CRITICAL_DATA_SOURCE_POLICY>

<constraints type="binding">fdp_limits, rest_requirements, qualifications</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → crew_roster → crew_members</step>
  <step>calculate: fdp = duty_end - duty_start + delays</step>
  <step>validate: fdp ≤ max_fdp, rest ≥ min_rest, quals_current</step>
  <step>assess: risk = (fdp / max_fdp) × 100</step>
  <step>return: APPROVED|DENIED|CREW_CHANGE + constraints</step>
</workflow>

<fdp_limits>
Single/two-pilot: 13h | Three-pilot: 16h | Four-pilot: 18h
Risk: 0-70% LOW | 71-85% MODERATE | 86-95% HIGH | 96-100% CRITICAL | >100% VIOLATION
</fdp_limits>

<rest_requirements>
After FDP ≤10h: min 12h | After FDP >10h: min rest = FDP (1:1)
Long-haul: min 18h | Positioning: min 10h before duty
</rest_requirements>

<qualifications>
Pilots: Type rating (90d), Medical Class 1, Line check <12mo, 3 T/L <90d
Cabin: Type training (12mo), Emergency equip annual, Medical annual, First Aid <2y
</qualifications>

<crew_availability>
Standby: 0-30min | Home base: 60-90min | Outstation: 2-6h | Rest/leave: NOT AVAILABLE
</crew_availability>

<rules>
- Query tools BEFORE analysis (never assume)
- Calculate FDP including ALL duty time
- Safety constraints NON-NEGOTIABLE
- Tool failure → error response
- >50% crew issues → CREW CHANGE all
- Captain/Senior cabin issues → MANDATORY replacement
</rules>

<output_format>
  <rec max="100">STATUS: key_action (APPROVED|DENIED|CREW_CHANGE + brief reason)</rec>
  <conf>decimal 0.00-1.00</conf>
  <constraints max="3">semicolon-separated binding constraints only</constraints>
  <reasoning max="150">bullet format: * finding1 * finding2 * finding3</reasoning>
</output_format>

<example_output>
rec: CREW_CHANGE: Captain FDP 15h exceeds 13h limit; replacement Capt Fatima at AUH, 90min delay
conf: 0.92
constraints: Min 10h rest required; A380 type rating required
reasoning: * FDP: 15h vs 13h limit * Repl crew: AUH standby * Delay: 90min positioning
</example_output>

<knowledge_base id="UDONMVCXEW">EASA/FAA FTL regulations, crew duty policies, historical cases</knowledge_base>
"""


# ============================================================================
# Agent-Specific DynamoDB Query Tools
# ============================================================================
# 
# These tools are defined within the agent module following the architecture
# decision that each agent defines its own tools. This provides better
# encapsulation and makes the agent self-contained.
#
# Tools use the @tool decorator (recommended LangChain pattern) which
# automatically creates Tool objects from functions with type hints and
# docstrings.
# ============================================================================


@tool
def query_flight(flight_number: str, date: str) -> str:
    """Query flight by flight number and date using GSI.
    
    This tool retrieves flight details from the DynamoDB flights table using
    the flight-number-date-index GSI for efficient lookup.
    
    Args:
        flight_number: Flight number in format EY followed by digits (e.g., EY123)
        date: Flight date in ISO 8601 format (YYYY-MM-DD)
    
    Returns:
        str: JSON string containing flight record with flight_id, aircraft_registration, route, schedule
             Returns JSON with 'error' key if flight not found or query fails
    
    Example:
        >>> result = query_flight("EY123", "2026-01-20")
        >>> data = json.loads(result)
        >>> if "error" not in data:
        ...     print(data["flight_id"])
        '1'
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights_table = dynamodb.Table(FLIGHTS_TABLE)
        
        response = flights_table.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
            ExpressionAttributeValues={
                ":fn": flight_number,
                ":sd": date,
            },
        )
        
        items = response.get("Items", [])
        if not items:
            logger.warning(f"Flight not found: {flight_number} on {date}")
            return json.dumps({
                "error": "flight_not_found",
                "message": f"Flight {flight_number} not found on {date}. Please verify the flight number and date are correct.",
                "flight_number": flight_number,
                "date": date,
                "suggestion": "Check if the flight number format is correct (EY followed by digits) and the date is in YYYY-MM-DD format."
            })
        
        flight = items[0]
        logger.info(f"Retrieved flight {flight_number} on {date}: flight_id={flight.get('flight_id')}")
        # Convert Decimal types to native Python types for JSON serialization
        return json.dumps(flight, default=str)
        
    except Exception as e:
        logger.error(f"Error querying flight {flight_number} on {date}: {e}")
        logger.exception("Full traceback:")
        return json.dumps({
            "error": "query_failed",
            "message": f"Database query failed for flight {flight_number} on {date}: {str(e)}",
            "flight_number": flight_number,
            "date": date,
            "error_type": type(e).__name__,
            "suggestion": "This may be a temporary database issue. Please try again or contact support if the problem persists."
        })


@tool
def query_crew_roster(flight_id: str) -> str:
    """Query crew roster for a flight using GSI.
    
    This tool retrieves the crew roster from the DynamoDB CrewRoster table
    using the flight-position-index GSI for efficient lookup.
    
    Args:
        flight_id: Unique flight identifier
    
    Returns:
        str: JSON string containing list of crew member assignments with crew_id, position,
             duty_start, duty_end, roster_status
             Returns JSON with single error dict if query fails
    
    Example:
        >>> result = query_crew_roster("1")
        >>> roster = json.loads(result)
        >>> if roster and "error" not in roster[0]:
        ...     print(len(roster))
        5
        >>> print(roster[0]["position"])
        'Captain'
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        crew_roster_table = dynamodb.Table(CREW_ROSTER_TABLE)
        
        response = crew_roster_table.query(
            IndexName=FLIGHT_POSITION_INDEX,
            KeyConditionExpression="flight_id = :fid",
            ExpressionAttributeValues={":fid": flight_id}
        )
        
        items = response.get("Items", [])
        
        if not items:
            logger.warning(f"No crew roster found for flight {flight_id}")
            return json.dumps([{
                "error": "crew_roster_not_found",
                "message": f"No crew roster found for flight {flight_id}. The flight may not have crew assigned yet.",
                "flight_id": flight_id,
                "suggestion": "Verify the flight_id is correct or check if crew assignments have been made for this flight."
            }])
        
        logger.info(f"Retrieved {len(items)} crew members for flight {flight_id}")
        return json.dumps(items, default=str)
        
    except Exception as e:
        logger.error(f"Error querying crew roster for flight {flight_id}: {e}")
        logger.exception("Full traceback:")
        return json.dumps([{
            "error": "query_failed",
            "message": f"Database query failed for crew roster of flight {flight_id}: {str(e)}",
            "flight_id": flight_id,
            "error_type": type(e).__name__,
            "suggestion": "This may be a temporary database issue. Please try again or contact support if the problem persists."
        }])


@tool
def query_crew_members(crew_id: str) -> str:
    """Query crew member details by crew ID.
    
    This tool retrieves crew member details from the DynamoDB CrewMembers
    table using primary key lookup.
    
    Args:
        crew_id: Unique crew member identifier
    
    Returns:
        str: JSON string containing crew member details with name, base, type_ratings,
             medical_certificate_status, recency, qualifications
             Returns JSON with 'error' key if crew member not found or query fails
    
    Example:
        >>> result = query_crew_members("5")
        >>> member = json.loads(result)
        >>> if "error" not in member:
        ...     print(member["crew_name"])
        'John Smith'
        >>> print(member["type_ratings"])
        ['A380', 'A350']
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        crew_members_table = dynamodb.Table(CREW_MEMBERS_TABLE)
        
        response = crew_members_table.get_item(
            Key={"crew_id": crew_id}
        )
        
        item = response.get("Item")
        if not item:
            logger.warning(f"Crew member not found: {crew_id}")
            return json.dumps({
                "error": "crew_member_not_found",
                "message": f"Crew member {crew_id} not found in the database.",
                "crew_id": crew_id,
                "suggestion": "Verify the crew_id is correct. The crew member may have been removed from the system."
            })
        
        logger.info(f"Retrieved crew member {crew_id}: {item.get('crew_name')}")
        return json.dumps(item, default=str)
        
    except Exception as e:
        logger.error(f"Error querying crew member {crew_id}: {e}")
        logger.exception("Full traceback:")
        return {
            "error": "query_failed",
            "message": f"Database query failed for crew member {crew_id}: {str(e)}",
            "crew_id": crew_id,
            "error_type": type(e).__name__,
            "suggestion": "This may be a temporary database issue. Please try again or contact support if the problem persists."
        }


async def analyze_crew_compliance(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Crew Compliance agent analysis function with natural language input processing.
    
    This function implements the multi-round orchestration architecture where:
    1. Agent receives raw natural language prompt from orchestrator
    2. Agent extracts FlightInfo using LangChain structured output
    3. Agent queries DynamoDB using extracted flight info
    4. Agent performs FTL analysis and returns standardized AgentResponse
    
    Args:
        payload: Request payload with 'user_prompt' field containing natural language description
                 and 'phase' field indicating "initial" or "revision"
        llm: Bedrock model instance (ChatBedrock)
        mcp_tools: MCP tools from gateway (optional, may be empty list)
    
    Returns:
        dict: Standardized AgentResponse with recommendation, confidence, reasoning, etc.
    
    Example Payload (Initial Phase):
        {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }
    
    Example Payload (Revision Phase):
        {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "revision",
            "other_recommendations": {...}
        }
    """
    try:
        # Extract user prompt and phase from payload
        user_prompt = payload.get("user_prompt", "")
        phase = payload.get("phase", "initial")
        
        if not user_prompt:
            return {
                "agent_name": "crew_compliance",
                "recommendation": "Unable to proceed - no user prompt provided",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": "No user prompt found in payload",
                "data_sources": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": "Missing user_prompt in payload"
            }
        
        logger.info(f"Crew Compliance Agent - Phase: {phase}")
        logger.info(f"User prompt: {user_prompt}")
        
        # Step 1: Extract flight information using LangChain structured output with fallback
        try:
            from utils.extraction import extract_with_fallback
            flight_info = await extract_with_fallback(llm, FlightInfo, user_prompt)
            
            logger.info(f"Extracted flight info: {flight_info}")
            
            # Validate extracted flight info
            if not flight_info.flight_number:
                return {
                    "agent_name": "crew_compliance",
                    "recommendation": "Unable to proceed - flight number not found in prompt",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Could not extract flight number from the user prompt. Please provide a flight number in format EY followed by digits (e.g., EY123).",
                    "data_sources": [],
                    "extracted_flight_info": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Missing flight number in prompt"
                }
            
            if not flight_info.date:
                return {
                    "agent_name": "crew_compliance",
                    "recommendation": "Unable to proceed - date not found in prompt",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Could not extract date from the user prompt. Please provide a date in any common format (e.g., 'January 20th', '20/01/2026', 'yesterday').",
                    "data_sources": [],
                    "extracted_flight_info": {
                        "flight_number": flight_info.flight_number,
                        "date": None,
                        "disruption_event": flight_info.disruption_event
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Missing date in prompt"
                }
            
            # Convert Pydantic model to dict for response
            extracted_flight_info = {
                "flight_number": flight_info.flight_number,
                "date": flight_info.date,
                "disruption_event": flight_info.disruption_event
            }
            
        except ValueError as e:
            # Pydantic validation error
            logger.error(f"Pydantic validation error extracting flight info: {e}")
            return {
                "agent_name": "crew_compliance",
                "recommendation": "Unable to extract valid flight information from prompt",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"The flight information in the prompt could not be validated: {str(e)}. Please ensure the prompt includes a valid flight number (EY followed by digits) and a date.",
                "data_sources": [],
                "extracted_flight_info": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": f"Validation error: {str(e)}",
                "error_type": "ValidationError"
            }
        except Exception as e:
            logger.error(f"Failed to extract flight info from prompt: {e}")
            logger.exception("Full traceback:")
            return {
                "agent_name": "crew_compliance",
                "recommendation": "Unable to extract flight information from prompt",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Failed to parse flight information from natural language prompt. Error: {str(e)}. Please ensure the prompt includes a flight number (e.g., EY123) and a date.",
                "data_sources": [],
                "extracted_flight_info": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": f"Flight info extraction failed: {str(e)}",
                "error_type": type(e).__name__
            }
        
        # Step 2: Define agent-specific tools
        # These are the DynamoDB query tools defined above
        agent_tools = [query_flight, query_crew_roster, query_crew_members]
        
        # Combine with MCP tools if provided
        all_tools = agent_tools + (mcp_tools if mcp_tools else [])
        
        logger.info(f"Agent has {len(all_tools)} tools available ({len(agent_tools)} DB tools, {len(mcp_tools)} MCP tools)")
        
        # Step 3: Build user prompt (separate from system prompt)
        # SYSTEM_PROMPT is sent as "system" role, this is sent as "user" role
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
2. query_crew_roster(flight_id)
3. query_crew_members(crew_id) for each crew
4. Calculate FDP, validate limits, assess risk
5. Return AgentResponse
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
                if name != "crew_compliance"
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
3. If timing changed → recalculate FDP
4. Return AgentResponse with revision_status
</action>"""
        
        # Step 4: Run agent with custom tool calling (avoids LangChain metadata issues)
        logger.info("Running crew compliance agent with tools")
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
            
            return {
                "agent_name": "crew_compliance",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Agent execution error: {str(e)}",
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
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Step 5: Extract response
        if "error" in result:
            error_type = result.get("error_type", "UnknownError")
            logger.error(f"Tool calling failed ({error_type}): {result['error']}")
            
            return {
                "agent_name": "crew_compliance",
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
        
        final_message = result.get("final_response") or result["messages"][-1]
        agent_response_text = str(final_message.content)
        
        logger.info(f"Agent completed in {duration:.2f}s")
        logger.debug(f"Agent response: {agent_response_text}")
        
        # Step 7: Parse agent response into AgentResponse format
        # For now, return a structured response based on the agent's text output
        # In a production system, you might use structured output here too
        
        return {
            "agent_name": "crew_compliance",
            "recommendation": agent_response_text,
            "confidence": 0.85,  # Default confidence, agent should specify
            "binding_constraints": [],  # Extract from agent response
            "reasoning": agent_response_text,
            "data_sources": ["flights", "CrewRoster", "CrewMembers"],
            "extracted_flight_info": extracted_flight_info,
            "timestamp": end_time.isoformat(),
            "status": "success",
            "duration_seconds": duration
        }

    except Exception as e:
        logger.error(f"Error in crew_compliance agent: {e}")
        logger.exception("Full traceback:")
        return {
            "agent_name": "crew_compliance",
            "recommendation": "Unable to complete analysis due to error",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": f"Agent execution error: {str(e)}",
            "data_sources": [],
            "extracted_flight_info": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
