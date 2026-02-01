"""
API Endpoints

This module provides functions for recording human solution selections
and managing decision records. This can be integrated with FastAPI or any
other web framework.

Note: FastAPI integration is optional. The core functions can be used
standalone or with any web framework.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from agents.schemas import DecisionRecord, ArbitratorOutput
from agents.s3_storage import store_decision_to_s3

logger = logging.getLogger(__name__)

# In-memory storage for arbitrator outputs (in production, use Redis or similar)
_arbitrator_outputs: Dict[str, ArbitratorOutput] = {}


class SolutionSelectionRequest(BaseModel):
    """Request body for solution selection"""
    disruption_id: str = Field(description="Unique identifier for the disruption")
    selected_solution_id: int = Field(description="ID of the solution selected by human (1, 2, or 3)")
    rationale: Optional[str] = Field(default=None, description="Why the human chose this solution")


class SolutionSelectionResponse(BaseModel):
    """Response for solution selection"""
    status: str = Field(description="Status: success, partial_success, or error")
    message: str = Field(description="Human-readable message")
    stored_to_buckets: Dict[str, bool] = Field(description="Storage status for each S3 bucket")


def register_arbitrator_output(disruption_id: str, output: ArbitratorOutput) -> None:
    """
    Register an arbitrator output for later retrieval.
    
    This function should be called by the orchestrator after arbitration completes
    to make the output available for the solution selection API.
    
    Args:
        disruption_id: Unique identifier for the disruption
        output: The arbitrator output with solution options
    """
    _arbitrator_outputs[disruption_id] = output
    logger.info(f"Registered arbitrator output for disruption {disruption_id}")


def get_arbitrator_output(disruption_id: str) -> Optional[ArbitratorOutput]:
    """
    Retrieve a registered arbitrator output.
    
    Args:
        disruption_id: Unique identifier for the disruption
        
    Returns:
        ArbitratorOutput if found, None otherwise
    """
    return _arbitrator_outputs.get(disruption_id)


def _extract_flight_number(output: ArbitratorOutput) -> str:
    """Extract flight number from arbitrator output or agent responses."""
    # Try to extract from reasoning or justification
    reasoning = output.reasoning or ""
    justification = output.justification or ""
    
    # Simple extraction - look for flight number pattern (e.g., EY123, AA456)
    import re
    pattern = r'\b[A-Z]{2}\d{3,4}\b'
    
    match = re.search(pattern, reasoning + " " + justification)
    if match:
        return match.group(0)
    
    return "UNKNOWN"


def _extract_disruption_type(output: ArbitratorOutput) -> str:
    """Extract disruption type from arbitrator output."""
    # Look for common disruption types in the reasoning
    reasoning = (output.reasoning or "").lower()
    justification = (output.justification or "").lower()
    text = reasoning + " " + justification
    
    if "crew" in text or "fdp" in text or "duty" in text:
        return "crew"
    elif "maintenance" in text or "aircraft" in text or "mechanical" in text:
        return "maintenance"
    elif "weather" in text:
        return "weather"
    elif "regulatory" in text or "curfew" in text or "slot" in text:
        return "regulatory"
    else:
        return "other"


def _extract_agent_responses(output: ArbitratorOutput) -> Dict[str, Any]:
    """
    Extract agent responses from arbitrator output.
    
    Note: In production, this should be passed from the orchestrator.
    For now, we reconstruct minimal info from the arbitrator output.
    """
    return {
        "conflicts_identified": [c.model_dump() for c in output.conflicts_identified],
        "conflict_resolutions": [r.model_dump() for r in output.conflict_resolutions],
        "safety_overrides": [s.model_dump() for s in output.safety_overrides]
    }


async def handle_solution_selection(request: SolutionSelectionRequest) -> SolutionSelectionResponse:
    """
    Handle solution selection request.
    
    This is the core business logic for recording a human's solution selection.
    Can be called directly or wrapped in a web framework endpoint.
    
    Args:
        request: Selection request with disruption_id, selected_solution_id, rationale
        
    Returns:
        Response with status and confirmation
        
    Raises:
        ValueError: If disruption_id not found or invalid solution_id
        Exception: If storage fails
        
    Example:
        >>> request = SolutionSelectionRequest(
        ...     disruption_id="DISR-2026-001",
        ...     selected_solution_id=2,
        ...     rationale="Balances cost and passenger impact"
        ... )
        >>> response = await handle_solution_selection(request)
        >>> print(response.status)
        success
    """
    # Load arbitrator output for this disruption
    arbitrator_output = get_arbitrator_output(request.disruption_id)
    
    if not arbitrator_output:
        raise ValueError(
            f"Disruption {request.disruption_id} not found. "
            "Arbitrator output must be registered before solution selection."
        )
    
    # Check if solution_options exists (multi-solution mode)
    if not arbitrator_output.solution_options:
        raise ValueError(
            f"Disruption {request.disruption_id} does not have solution options. "
            "This endpoint requires multi-solution arbitrator output."
        )
    
    # Validate selected solution ID exists
    valid_ids = [s.solution_id for s in arbitrator_output.solution_options]
    if request.selected_solution_id not in valid_ids:
        raise ValueError(
            f"Invalid solution ID {request.selected_solution_id}. "
            f"Valid IDs: {valid_ids}"
        )
    
    # Create decision record
    decision_record = DecisionRecord(
        disruption_id=request.disruption_id,
        timestamp=arbitrator_output.timestamp,
        flight_number=_extract_flight_number(arbitrator_output),
        disruption_type=_extract_disruption_type(arbitrator_output),
        disruption_severity="medium",  # Could be derived from agent responses
        agent_responses=_extract_agent_responses(arbitrator_output),
        solution_options=arbitrator_output.solution_options,
        recommended_solution_id=arbitrator_output.recommended_solution_id,
        conflicts_identified=arbitrator_output.conflicts_identified,
        conflict_resolutions=arbitrator_output.conflict_resolutions,
        selected_solution_id=request.selected_solution_id,
        selection_rationale=request.rationale,
        human_override=(
            request.selected_solution_id != arbitrator_output.recommended_solution_id
        )
    )
    
    # Store to S3
    storage_results = await store_decision_to_s3(decision_record)
    
    # Check if storage succeeded
    all_success = all(storage_results.values())
    
    return SolutionSelectionResponse(
        status="success" if all_success else "partial_success",
        message=(
            "Decision recorded for historical learning"
            if all_success
            else "Decision recorded but some storage operations failed"
        ),
        stored_to_buckets=storage_results
    )


def get_disruption_status(disruption_id: str) -> Dict[str, Any]:
    """
    Get the status of a disruption and its arbitrator output.
    
    Args:
        disruption_id: Unique identifier for the disruption
        
    Returns:
        Disruption status and solution options
        
    Raises:
        ValueError: If disruption not found
    """
    arbitrator_output = get_arbitrator_output(disruption_id)
    
    if not arbitrator_output:
        raise ValueError(f"Disruption {disruption_id} not found")
    
    return {
        "disruption_id": disruption_id,
        "timestamp": arbitrator_output.timestamp,
        "final_decision": arbitrator_output.final_decision,
        "solution_count": len(arbitrator_output.solution_options) if arbitrator_output.solution_options else 0,
        "recommended_solution_id": arbitrator_output.recommended_solution_id,
        "confidence": arbitrator_output.confidence
    }


def health_check() -> Dict[str, Any]:
    """Health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "registered_disruptions": len(_arbitrator_outputs)
    }


# FastAPI integration (optional - only if FastAPI is installed)
try:
    from fastapi import APIRouter, HTTPException
    
    router = APIRouter()
    
    @router.post("/api/select-solution", response_model=SolutionSelectionResponse)
    async def select_solution(request: SolutionSelectionRequest):
        """FastAPI endpoint for solution selection."""
        try:
            return await handle_solution_selection(request)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to record solution selection: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/api/disruption/{disruption_id}")
    async def get_disruption(disruption_id: str):
        """FastAPI endpoint for getting disruption status."""
        try:
            return get_disruption_status(disruption_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @router.get("/api/health")
    async def health():
        """FastAPI health check endpoint."""
        return health_check()
    
    logger.info("FastAPI router initialized")
    
except ImportError:
    logger.info("FastAPI not installed - using standalone functions only")
    router = None
