"""
Property-Based Tests for Agent Module Import Integrity

Feature: skymarshal-agent-rearchitecture
Property 1: Module Import Integrity
Validates: Requirements 2.2, 2.5

For any agent module in the agents directory, importing its analysis function
should succeed without errors and return a callable function.
"""

import importlib
from hypothesis import given, strategies as st, settings


@given(agent_name=st.sampled_from([
    "crew_compliance", "maintenance", "regulatory",
    "network", "guest_experience", "cargo", "finance"
]))
@settings(max_examples=100, deadline=None)
def test_agent_module_import_integrity(agent_name):
    """
    Property 1: Module Import Integrity (extended)
    
    For any agent module, importing its analysis function should succeed
    without errors and return a callable function.
    
    Tests all 7 agents: 3 safety agents + 4 business agents
    
    Validates: Requirements 2.2, 2.5
    """
    # Import the agent module
    module = importlib.import_module(f"agents.{agent_name}")
    
    # Get the analyze function
    analyze_fn_name = f"analyze_{agent_name}"
    assert hasattr(module, analyze_fn_name), \
        f"Module agents.{agent_name} should export {analyze_fn_name}"
    
    analyze_fn = getattr(module, analyze_fn_name)
    
    # Verify it's callable
    assert callable(analyze_fn), \
        f"{analyze_fn_name} should be a callable function"
    
    # Verify it's an async function
    import inspect
    assert inspect.iscoroutinefunction(analyze_fn), \
        f"{analyze_fn_name} should be an async function"


def test_crew_compliance_import_basic():
    """
    Basic unit test for crew_compliance import
    
    Validates that the crew_compliance agent can be imported and has
    the expected analyze function.
    """
    from agents.crew_compliance import analyze_crew_compliance
    
    # Verify function exists and is callable
    assert callable(analyze_crew_compliance)
    
    # Verify it's an async function
    import inspect
    assert inspect.iscoroutinefunction(analyze_crew_compliance)
    
    # Verify function signature
    sig = inspect.signature(analyze_crew_compliance)
    params = list(sig.parameters.keys())
    assert "payload" in params
    assert "llm" in params
    assert "mcp_tools" in params
