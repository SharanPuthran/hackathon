"""System test script for SkyMarshal"""

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database():
    """Test database connection"""
    logger.info("Testing database connection...")
    try:
        from src.database import DatabaseManager
        db = DatabaseManager()
        await db.initialize()
        
        # Test query
        flights = await db.get_all_flights()
        logger.info(f"✅ Database OK - Found {len(flights)} flights")
        
        await db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False


async def test_model_providers():
    """Test model provider initialization"""
    logger.info("Testing model providers...")
    try:
        from src.model_providers import ModelFactory, create_bedrock_client
        
        # Test Bedrock (only provider)
        bedrock_client = create_bedrock_client()
        logger.info("✅ Bedrock client created")
        
        # Test model factory
        model_factory = ModelFactory(bedrock_client=bedrock_client)
        
        # Test getting a provider
        provider = model_factory.get_provider("crew_compliance_agent")
        logger.info(f"✅ Model provider OK - {provider.__class__.__name__}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Model provider test failed: {e}")
        return False


async def test_agents():
    """Test agent initialization"""
    logger.info("Testing agent initialization...")
    try:
        from src.database import DatabaseManager
        from src.model_providers import ModelFactory, create_bedrock_client
        from src.agents import CrewComplianceAgent, NetworkAgent, SkyMarshalArbitrator
        
        db = DatabaseManager()
        await db.initialize()
        
        bedrock_client = create_bedrock_client()
        model_factory = ModelFactory(bedrock_client=bedrock_client)
        
        # Test safety agent
        crew_agent = CrewComplianceAgent(model_factory, db)
        logger.info(f"✅ Safety agent OK - {crew_agent.name}")
        
        # Test business agent
        network_agent = NetworkAgent(model_factory, db)
        logger.info(f"✅ Business agent OK - {network_agent.name}")
        
        # Test arbitrator
        arbitrator = SkyMarshalArbitrator(model_factory, db)
        logger.info(f"✅ Arbitrator OK - {arbitrator.name}")
        
        await db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Agent test failed: {e}")
        return False


async def test_orchestrator():
    """Test orchestrator initialization"""
    logger.info("Testing orchestrator...")
    try:
        from src.database import DatabaseManager
        from src.model_providers import ModelFactory, create_bedrock_client
        from src.orchestrator import SkyMarshalOrchestrator
        
        db = DatabaseManager()
        await db.initialize()
        
        bedrock_client = create_bedrock_client()
        model_factory = ModelFactory(bedrock_client=bedrock_client)
        
        orchestrator = SkyMarshalOrchestrator(model_factory, db)
        logger.info(f"✅ Orchestrator OK - {len(orchestrator.safety_agents)} safety agents, {len(orchestrator.business_agents)} business agents")
        
        await db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Orchestrator test failed: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("SkyMarshal System Test")
    logger.info("=" * 60)
    logger.info("")
    
    tests = [
        ("Database", test_database),
        ("Model Providers", test_model_providers),
        ("Agents", test_agents),
        ("Orchestrator", test_orchestrator)
    ]
    
    results = []
    
    for name, test_func in tests:
        logger.info(f"\n--- Testing {name} ---")
        result = await test_func()
        results.append((name, result))
        logger.info("")
    
    # Summary
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {name}")
        if not result:
            all_passed = False
    
    logger.info("")
    if all_passed:
        logger.info("🎉 All tests passed! System is ready.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run CLI demo: python run_demo.py")
        logger.info("  2. Run dashboard: streamlit run app.py")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check configuration.")
        logger.error("")
        logger.error("Common issues:")
        logger.error("  - Database not running or not populated")
        logger.error("  - API keys not configured in .env")
        logger.error("  - Missing dependencies")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
