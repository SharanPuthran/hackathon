"""Validation utilities for orchestrator and agents"""

from typing import Dict, Any
from agents.schemas import OrchestratorValidation


def validate_disruption_payload(payload: Dict[str, Any]) -> OrchestratorValidation:
    """
    Validate that all required information is present in the disruption payload.

    Args:
        payload: The request payload containing disruption data

    Returns:
        OrchestratorValidation: Validation result with missing fields and errors
    """
    required_fields = [
        "disruption.flight.flight_id",
        "disruption.flight.flight_number",
        "disruption.flight.departure_airport",
        "disruption.flight.arrival_airport",
        "disruption.flight.scheduled_departure",
        "disruption.flight.aircraft_id",
        "disruption.delay_hours",
        "disruption.disruption_type",
    ]

    # Field descriptions for better error messages
    field_descriptions = {
        "disruption.flight.flight_id": "Unique identifier for the flight (e.g., '1', '123')",
        "disruption.flight.flight_number": "Flight number (e.g., 'EY123', 'AA456')",
        "disruption.flight.departure_airport": "IATA departure airport code (e.g., 'AUH', 'JFK')",
        "disruption.flight.arrival_airport": "IATA arrival airport code (e.g., 'LHR', 'LAX')",
        "disruption.flight.scheduled_departure": "Scheduled departure time (ISO 8601 format)",
        "disruption.flight.aircraft_id": "Aircraft identifier (e.g., 'A6-APX', 'N12345')",
        "disruption.delay_hours": "Delay duration in hours (numeric value, e.g., 3, 5.5)",
        "disruption.disruption_type": "Type of disruption (e.g., 'technical', 'weather', 'crew')",
    }

    missing_fields = []
    validation_errors = []
    missing_field_details = []

    # Check if disruption key exists
    if "disruption" not in payload:
        return OrchestratorValidation(
            is_valid=False,
            missing_fields=["disruption"],
            validation_errors=[
                "Missing 'disruption' key in payload. The payload must contain a 'disruption' object with flight and disruption details."
            ],
            required_fields=required_fields,
        )

    disruption = payload["disruption"]

    # Check each required field
    for field_path in required_fields:
        parts = field_path.split(".")
        current = disruption

        try:
            # Navigate through nested structure
            for part in parts[1:]:  # Skip 'disruption' prefix
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    missing_fields.append(field_path)
                    description = field_descriptions.get(field_path, "No description available")
                    missing_field_details.append(f"{field_path}: {description}")
                    validation_errors.append(
                        f"Missing required field '{field_path}'. Expected: {description}"
                    )
                    break
            else:
                # Check if final value is None or empty
                if current is None or (
                    isinstance(current, str) and not current.strip()
                ):
                    missing_fields.append(field_path)
                    description = field_descriptions.get(field_path, "No description available")
                    missing_field_details.append(f"{field_path}: {description}")
                    validation_errors.append(
                        f"Field '{field_path}' is empty or None. Expected: {description}"
                    )
        except (KeyError, TypeError) as e:
            missing_fields.append(field_path)
            description = field_descriptions.get(field_path, "No description available")
            missing_field_details.append(f"{field_path}: {description}")
            validation_errors.append(
                f"Error accessing '{field_path}': {str(e)}. Expected: {description}"
            )

    # Additional validation rules
    if "delay_hours" in disruption:
        try:
            delay = float(disruption["delay_hours"])
            if delay < 0:
                validation_errors.append(
                    "delay_hours must be non-negative. Received: " + str(delay)
                )
        except (ValueError, TypeError):
            validation_errors.append(
                f"delay_hours must be a valid number. Received: {disruption.get('delay_hours')} (type: {type(disruption.get('delay_hours')).__name__})"
            )

    is_valid = len(missing_fields) == 0 and len(validation_errors) == 0

    # Add helpful summary if validation failed
    if not is_valid:
        summary = f"\n\nValidation Summary:\n- Total missing/invalid fields: {len(missing_fields)}\n- Missing fields:\n  " + "\n  ".join(missing_field_details)
        validation_errors.append(summary)

    return OrchestratorValidation(
        is_valid=is_valid,
        missing_fields=missing_fields,
        validation_errors=validation_errors,
        required_fields=required_fields,
    )


def validate_agent_requirements(
    agent_name: str, payload: Dict[str, Any]
) -> OrchestratorValidation:
    """
    Validate agent-specific requirements.

    Args:
        agent_name: Name of the agent
        payload: The request payload

    Returns:
        OrchestratorValidation: Validation result
    """
    agent_requirements = {
        "crew_compliance": [
            "disruption.flight.flight_id",
            "disruption.delay_hours",
        ],
        "maintenance": [
            "disruption.flight.aircraft_id",
            "disruption.flight.flight_id",
        ],
        "regulatory": [
            "disruption.flight.departure_airport",
            "disruption.flight.arrival_airport",
            "disruption.flight.scheduled_departure",
        ],
        "network": [
            "disruption.flight.flight_id",
            "disruption.flight.aircraft_id",
            "disruption.delay_hours",
        ],
        "guest_experience": [
            "disruption.flight.flight_id",
            "disruption.delay_hours",
        ],
        "cargo": [
            "disruption.flight.flight_id",
            "disruption.delay_hours",
        ],
        "finance": [
            "disruption.flight.flight_id",
            "disruption.delay_hours",
        ],
    }

    # Field descriptions for better error messages
    field_descriptions = {
        "disruption.flight.flight_id": "Unique identifier for the flight (e.g., '1', '123')",
        "disruption.flight.flight_number": "Flight number (e.g., 'EY123', 'AA456')",
        "disruption.flight.departure_airport": "IATA departure airport code (e.g., 'AUH', 'JFK')",
        "disruption.flight.arrival_airport": "IATA arrival airport code (e.g., 'LHR', 'LAX')",
        "disruption.flight.scheduled_departure": "Scheduled departure time (ISO 8601 format)",
        "disruption.flight.aircraft_id": "Aircraft identifier (e.g., 'A6-APX', 'N12345')",
        "disruption.delay_hours": "Delay duration in hours (numeric value, e.g., 3, 5.5)",
        "disruption.disruption_type": "Type of disruption (e.g., 'technical', 'weather', 'crew')",
    }

    # Agent-specific field purposes
    agent_field_purposes = {
        "crew_compliance": {
            "disruption.flight.flight_id": "Required to query crew roster and FDP calculations",
            "disruption.delay_hours": "Required to calculate FDP impact and crew availability",
        },
        "maintenance": {
            "disruption.flight.aircraft_id": "Required to query MEL status and maintenance history",
            "disruption.flight.flight_id": "Required to assess flight-specific maintenance constraints",
        },
        "regulatory": {
            "disruption.flight.departure_airport": "Required to check departure curfews and slot restrictions",
            "disruption.flight.arrival_airport": "Required to check arrival curfews and regulatory constraints",
            "disruption.flight.scheduled_departure": "Required to calculate curfew violations and slot timing",
        },
        "network": {
            "disruption.flight.flight_id": "Required to query downstream connections and propagation",
            "disruption.flight.aircraft_id": "Required to assess aircraft rotation impact",
            "disruption.delay_hours": "Required to calculate network propagation effects",
        },
        "guest_experience": {
            "disruption.flight.flight_id": "Required to query passenger manifest and connection data",
            "disruption.delay_hours": "Required to calculate compensation and rebooking needs",
        },
        "cargo": {
            "disruption.flight.flight_id": "Required to query cargo manifest and AWB data",
            "disruption.delay_hours": "Required to assess cold chain viability and perishable impact",
        },
        "finance": {
            "disruption.flight.flight_id": "Required to calculate direct costs and revenue impact",
            "disruption.delay_hours": "Required to calculate time-based costs and compensation",
        },
    }

    required = agent_requirements.get(agent_name, [])
    missing_fields = []
    validation_errors = []
    missing_field_details = []

    if "disruption" not in payload:
        return OrchestratorValidation(
            is_valid=False,
            missing_fields=["disruption"],
            validation_errors=[
                f"Agent '{agent_name}' requires 'disruption' key in payload. "
                f"The disruption object must contain flight and disruption details."
            ],
            required_fields=required,
        )

    disruption = payload["disruption"]

    for field_path in required:
        parts = field_path.split(".")
        current = disruption

        try:
            for part in parts[1:]:  # Skip 'disruption' prefix
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    missing_fields.append(field_path)
                    description = field_descriptions.get(field_path, "No description available")
                    purpose = agent_field_purposes.get(agent_name, {}).get(field_path, "Required for agent analysis")
                    missing_field_details.append(
                        f"  • {field_path}\n    Description: {description}\n    Purpose: {purpose}"
                    )
                    break
            else:
                if current is None or (
                    isinstance(current, str) and not current.strip()
                ):
                    missing_fields.append(field_path)
                    description = field_descriptions.get(field_path, "No description available")
                    purpose = agent_field_purposes.get(agent_name, {}).get(field_path, "Required for agent analysis")
                    missing_field_details.append(
                        f"  • {field_path}\n    Description: {description}\n    Purpose: {purpose}\n    Issue: Field is empty or None"
                    )
        except (KeyError, TypeError) as e:
            missing_fields.append(field_path)
            description = field_descriptions.get(field_path, "No description available")
            purpose = agent_field_purposes.get(agent_name, {}).get(field_path, "Required for agent analysis")
            missing_field_details.append(
                f"  • {field_path}\n    Description: {description}\n    Purpose: {purpose}\n    Error: {str(e)}"
            )

    is_valid = len(missing_fields) == 0

    if not is_valid:
        error_message = (
            f"Agent '{agent_name}' cannot proceed due to missing required information.\n\n"
            f"Missing Fields ({len(missing_fields)}):\n" + "\n".join(missing_field_details) +
            f"\n\nTo resolve: Please provide all required fields in the 'disruption' object of your payload."
        )
        validation_errors.append(error_message)

    return OrchestratorValidation(
        is_valid=is_valid,
        missing_fields=missing_fields,
        validation_errors=validation_errors,
        required_fields=required,
    )
