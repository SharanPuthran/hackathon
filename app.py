"""Streamlit dashboard for SkyMarshal demo"""

import streamlit as st
import asyncio
import logging
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath('.'))

from src.database import DatabaseManager
from src.model_providers import ModelFactory, create_bedrock_client
from src.orchestrator import SkyMarshalOrchestrator
from src.models import DisruptionEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="SkyMarshal - Disruption Management",
    page_icon="✈️",
    layout="wide"
)

# Initialize session state
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = None
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = None
if 'result' not in st.session_state:
    st.session_state.result = None
if 'running' not in st.session_state:
    st.session_state.running = False


async def initialize_system():
    """Initialize database and orchestrator"""
    if st.session_state.db_manager is None:
        try:
            db_manager = DatabaseManager()
            await db_manager.initialize()
            st.session_state.db_manager = db_manager
            
            # Initialize model factory (All via Bedrock)
            bedrock_client = create_bedrock_client()
            model_factory = ModelFactory(bedrock_client=bedrock_client)
            
            # Initialize orchestrator
            orchestrator = SkyMarshalOrchestrator(model_factory, db_manager)
            st.session_state.orchestrator = orchestrator
            
            return True
        except Exception as e:
            st.error(f"Failed to initialize system: {e}")
            logger.error(f"Initialization error: {e}")
            return False
    return True


async def run_disruption_scenario(disruption: DisruptionEvent):
    """Run disruption management workflow"""
    st.session_state.running = True
    
    try:
        result = await st.session_state.orchestrator.run(disruption)
        st.session_state.result = result
        st.session_state.running = False
        return result
    except Exception as e:
        st.error(f"Workflow failed: {e}")
        logger.error(f"Workflow error: {e}")
        st.session_state.running = False
        return None


def main():
    """Main Streamlit app"""
    
    st.title("🛫 SkyMarshal - Agentic Airline Disruption Management")
    st.markdown("**Multi-Agent AI System for Etihad Airways**")
    
    # Sidebar
    with st.sidebar:
        st.header("System Status")
        
        if st.button("Initialize System"):
            with st.spinner("Initializing..."):
                success = asyncio.run(initialize_system())
                if success:
                    st.success("✅ System initialized")
                else:
                    st.error("❌ Initialization failed")
        
        if st.session_state.orchestrator:
            st.success("🟢 System Ready")
        else:
            st.warning("🟡 System Not Initialized")
        
        st.markdown("---")
        st.markdown("### Demo Scenarios")
        st.markdown("""
        1. **Hydraulic Failure** (Technical)
        2. **Crew Timeout** (FTL)
        3. **Weather Diversion** (ATC)
        """)
    
    # Main content
    if not st.session_state.orchestrator:
        st.info("👈 Click 'Initialize System' in the sidebar to begin")
        return
    
    # Demo scenario selection
    st.header("Create Disruption Event")
    
    col1, col2 = st.columns(2)
    
    with col1:
        flight_number = st.text_input("Flight Number", value="EY551")
        aircraft_code = st.selectbox("Aircraft", ["A380", "A350", "B787-9", "A321"])
        origin = st.text_input("Origin", value="LHR")
        destination = st.text_input("Destination", value="AUH")
    
    with col2:
        disruption_type = st.selectbox(
            "Disruption Type",
            ["technical", "crew", "weather", "atc", "other"]
        )
        severity = st.selectbox("Severity", ["low", "medium", "high", "critical"])
        description = st.text_area(
            "Description",
            value="Hydraulic system failure detected during pre-flight check"
        )
    
    if st.button("🚀 Run Disruption Management", type="primary", disabled=st.session_state.running):
        # Create disruption event
        disruption = DisruptionEvent(
            flight_id=1,  # Placeholder
            flight_number=flight_number,
            aircraft_id="A6-BND",
            aircraft_code=aircraft_code,
            origin=origin,
            destination=destination,
            scheduled_departure=datetime.now() + timedelta(hours=2),
            disruption_type=disruption_type,
            description=description,
            severity=severity
        )
        
        with st.spinner("Running multi-agent workflow..."):
            result = asyncio.run(run_disruption_scenario(disruption))
    
    # Display results
    if st.session_state.result:
        result = st.session_state.result
        
        st.success("✅ Workflow Completed")
        
        # Phase tracker
        st.header("Workflow Progress")
        phases = ["Trigger", "Safety", "Impact", "Options", "Arbitration", "Approval", "Execution"]
        current_phase = result.get("current_phase", "trigger")
        
        cols = st.columns(len(phases))
        for i, (col, phase) in enumerate(zip(cols, phases)):
            with col:
                if phase.lower() in current_phase.lower():
                    st.success(f"✅ {phase}")
                else:
                    st.info(f"⏳ {phase}")
        
        # Safety Constraints
        st.header("🔒 Safety Constraints")
        constraints = result.get("safety_constraints", [])
        if constraints:
            for constraint in constraints:
                with st.expander(f"{constraint['constraint_type']} - {constraint['agent_name']}"):
                    st.write(f"**Restriction:** {constraint['restriction']}")
                    st.caption(f"**Reasoning:** {constraint['reasoning'][:200]}...")
        else:
            st.info("No safety constraints identified")
        
        # Impact Assessments
        st.header("📊 Impact Assessment")
        impact_assessments = result.get("impact_assessments", {})
        if impact_assessments:
            cols = st.columns(len(impact_assessments))
            for col, (agent, impact) in zip(cols, impact_assessments.items()):
                with col:
                    st.metric(
                        agent.replace("_", " ").title(),
                        f"{impact.get('pax_affected', 0)} PAX",
                        f"${impact.get('cost_estimate', 0):,.0f}"
                    )
        
        # Ranked Scenarios
        st.header("🎯 Recommended Scenarios")
        ranked_scenarios = result.get("ranked_scenarios", [])
        if ranked_scenarios:
            for scenario_data in ranked_scenarios:
                scenario = scenario_data["scenario"]
                with st.expander(f"#{scenario_data['rank']}: {scenario['title']} (Score: {scenario_data['score']:.2f})"):
                    st.write(f"**Description:** {scenario['description']}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Delay", f"{scenario['estimated_delay']} min")
                    with col2:
                        st.metric("PAX Impacted", scenario['pax_impacted'])
                    with col3:
                        st.metric("Cost", f"${scenario['cost_estimate']:,.0f}")
                    
                    st.write("**Pros:**")
                    for pro in scenario_data.get("pros", []):
                        st.write(f"✅ {pro}")
                    
                    st.write("**Cons:**")
                    for con in scenario_data.get("cons", []):
                        st.write(f"⚠️ {con}")
                    
                    st.write("**Actions:**")
                    for action in scenario["actions"]:
                        st.write(f"- {action['type']}: {action['description']}")
        
        # Human Decision
        st.header("👤 Human Decision")
        human_decision = result.get("human_decision")
        if human_decision:
            st.success(f"✅ Approved by {human_decision['decision_maker']}")
            st.write(f"Chosen Scenario: {human_decision['chosen_scenario_id']}")
        
        # Execution Status
        if result.get("execution_complete"):
            st.header("⚙️ Execution Complete")
            st.success("All actions executed successfully")


if __name__ == "__main__":
    main()
