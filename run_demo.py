"""CLI runner for SkyMarshal demo"""

import asyncio
import logging
from datetime import datetime, timedelta

from src.database import DatabaseManager
from src.model_providers import ModelFactory, create_bedrock_client
from src.orchestrator import SkyMarshalOrchestrator
from src.models import DisruptionEvent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run demo scenario"""
    
    logger.info("=" * 60)
    logger.info("SkyMarshal - Agentic Airline Disruption Management")
    logger.info("=" * 60)
    
    # Initialize database
    logger.info("Initializing database...")
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Initialize model factory (All via Bedrock)
    logger.info("Initializing model providers...")
    bedrock_client = create_bedrock_client()
    model_factory = ModelFactory(bedrock_client=bedrock_client)
    
    # Initialize orchestrator
    logger.info("Initializing orchestrator...")
    orchestrator = SkyMarshalOrchestrator(model_factory, db_manager)
    
    # Create demo disruption
    disruption = DisruptionEvent(
        flight_id=1,
        flight_number="EY551",
        aircraft_id="A6-BND",
        aircraft_code="A380",
        origin="LHR",
        destination="AUH",
        scheduled_departure=datetime.now() + timedelta(hours=2),
        disruption_type="technical",
        description="Hydraulic system failure detected during pre-flight check. System B hydraulic pressure below minimum threshold.",
        severity="high"
    )
    
    logger.info(f"\nDisruption Event:")
    logger.info(f"  Flight: {disruption.flight_number}")
    logger.info(f"  Aircraft: {disruption.aircraft_code}")
    logger.info(f"  Route: {disruption.origin} → {disruption.destination}")
    logger.info(f"  Issue: {disruption.description}")
    logger.info(f"  Severity: {disruption.severity}")
    logger.info("")
    
    # Run workflow
    logger.info("Starting workflow...")
    result = await orchestrator.run(disruption)
    
    # Display results
    logger.info("\n" + "=" * 60)
    logger.info("WORKFLOW RESULTS")
    logger.info("=" * 60)
    
    logger.info(f"\nFinal Phase: {result['current_phase']}")
    
    logger.info(f"\nSafety Constraints: {len(result.get('safety_constraints', []))}")
    for constraint in result.get('safety_constraints', []):
        logger.info(f"  - {constraint['constraint_type']}: {constraint['restriction'][:100]}...")
    
    logger.info(f"\nImpact Assessments: {len(result.get('impact_assessments', {}))}")
    for agent, impact in result.get('impact_assessments', {}).items():
        logger.info(f"  - {agent}: PAX={impact.get('pax_affected', 0)}, Cost=${impact.get('cost_estimate', 0):,.0f}")
    
    logger.info(f"\nProposals: {len(result.get('agent_proposals', []))}")
    
    logger.info(f"\nRanked Scenarios: {len(result.get('ranked_scenarios', []))}")
    for scenario_data in result.get('ranked_scenarios', []):
        scenario = scenario_data['scenario']
        logger.info(f"  #{scenario_data['rank']}: {scenario['title']} (Score: {scenario_data['score']:.3f})")
        logger.info(f"    Delay: {scenario['estimated_delay']}min, Cost: ${scenario['cost_estimate']:,.0f}")
    
    if result.get('human_decision'):
        logger.info(f"\nHuman Decision: Approved")
    
    if result.get('execution_complete'):
        logger.info(f"\nExecution: Complete")
    
    logger.info("\n" + "=" * 60)
    logger.info("Demo completed successfully!")
    logger.info("=" * 60)
    
    # Cleanup
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
