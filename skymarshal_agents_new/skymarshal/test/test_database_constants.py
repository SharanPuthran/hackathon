"""
Unit tests for database constants module.

Tests validation functions, agent permissions, and constant integrity.
"""

import pytest
from database.constants import (
    # Table names
    FLIGHTS_TABLE,
    BOOKINGS_TABLE,
    CREW_ROSTER_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    # GSI names
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_ID_INDEX,
    FLIGHT_POSITION_INDEX,
    # Agent access
    AGENT_TABLE_ACCESS,
    AGENT_GSI_ACCESS,
    ALL_TABLES,
    ALL_GSIS,
    # Validation functions
    validate_agent_name,
    get_agent_tables,
    get_agent_gsis,
    can_agent_access_table,
    can_agent_use_gsi
)


class TestAgentValidation:
    """Test agent name validation."""

    def test_validate_valid_agent_names(self):
        """Test that all defined agents are valid."""
        valid_agents = [
            "crew_compliance",
            "maintenance",
            "regulatory",
            "network",
            "guest_experience",
            "cargo",
            "finance",
            "arbitrator"
        ]

        for agent in valid_agents:
            assert validate_agent_name(agent), f"Agent {agent} should be valid"

    def test_validate_invalid_agent_name(self):
        """Test that invalid agent names are rejected."""
        invalid_agents = [
            "invalid_agent",
            "orchestrator",
            "",
            "CREW_COMPLIANCE",  # Case sensitive
            "crew-compliance"  # Wrong separator
        ]

        for agent in invalid_agents:
            assert not validate_agent_name(agent), f"Agent {agent} should be invalid"


class TestAgentTableAccess:
    """Test agent table access permissions."""

    def test_get_agent_tables_crew_compliance(self):
        """Test crew compliance agent table access."""
        tables = get_agent_tables("crew_compliance")

        assert FLIGHTS_TABLE in tables
        assert CREW_ROSTER_TABLE in tables
        assert len(tables) == 3  # Should have exactly 3 tables

    def test_get_agent_tables_maintenance(self):
        """Test maintenance agent table access."""
        tables = get_agent_tables("maintenance")

        assert FLIGHTS_TABLE in tables
        assert MAINTENANCE_WORK_ORDERS_TABLE in tables
        assert len(tables) == 5  # Should have exactly 5 tables

    def test_get_agent_tables_invalid_agent(self):
        """Test that invalid agent raises ValueError."""
        with pytest.raises(ValueError, match="Unknown agent"):
            get_agent_tables("invalid_agent")

    def test_can_agent_access_table_authorized(self):
        """Test authorized table access."""
        assert can_agent_access_table("crew_compliance", FLIGHTS_TABLE)
        assert can_agent_access_table("maintenance", MAINTENANCE_WORK_ORDERS_TABLE)
        assert can_agent_access_table("guest_experience", BOOKINGS_TABLE)

    def test_can_agent_access_table_unauthorized(self):
        """Test unauthorized table access."""
        # Crew compliance should not access bookings
        assert not can_agent_access_table("crew_compliance", BOOKINGS_TABLE)

        # Network should not access crew roster
        assert not can_agent_access_table("network", CREW_ROSTER_TABLE)

    def test_can_agent_access_table_invalid_agent(self):
        """Test table access check with invalid agent."""
        assert not can_agent_access_table("invalid_agent", FLIGHTS_TABLE)


class TestAgentGSIAccess:
    """Test agent GSI access permissions."""

    def test_get_agent_gsis_crew_compliance(self):
        """Test crew compliance agent GSI access."""
        gsis = get_agent_gsis("crew_compliance")

        assert FLIGHT_NUMBER_DATE_INDEX in gsis
        assert FLIGHT_POSITION_INDEX in gsis

    def test_get_agent_gsis_guest_experience(self):
        """Test guest experience agent GSI access."""
        gsis = get_agent_gsis("guest_experience")

        assert FLIGHT_NUMBER_DATE_INDEX in gsis
        assert FLIGHT_ID_INDEX in gsis

    def test_get_agent_gsis_invalid_agent(self):
        """Test that invalid agent raises ValueError."""
        with pytest.raises(ValueError, match="Unknown agent"):
            get_agent_gsis("invalid_agent")

    def test_can_agent_use_gsi_authorized(self):
        """Test authorized GSI usage."""
        assert can_agent_use_gsi("crew_compliance", FLIGHT_NUMBER_DATE_INDEX)
        assert can_agent_use_gsi("guest_experience", FLIGHT_ID_INDEX)

    def test_can_agent_use_gsi_unauthorized(self):
        """Test unauthorized GSI usage."""
        # Network should not use flight-id-index (bookings GSI)
        assert not can_agent_use_gsi("network", FLIGHT_ID_INDEX)

    def test_can_agent_use_gsi_invalid_agent(self):
        """Test GSI usage check with invalid agent."""
        assert not can_agent_use_gsi("invalid_agent", FLIGHT_NUMBER_DATE_INDEX)


class TestArbitratorAccess:
    """Test arbitrator has comprehensive access."""

    def test_arbitrator_has_all_table_access(self):
        """Test that arbitrator can access all critical tables."""
        arbitrator_tables = get_agent_tables("arbitrator")

        # Arbitrator should have access to all major tables
        critical_tables = [
            FLIGHTS_TABLE,
            BOOKINGS_TABLE,
            CREW_ROSTER_TABLE,
            MAINTENANCE_WORK_ORDERS_TABLE
        ]

        for table in critical_tables:
            assert table in arbitrator_tables, f"Arbitrator should access {table}"

    def test_arbitrator_has_all_gsi_access(self):
        """Test that arbitrator can use all GSIs."""
        arbitrator_gsis = get_agent_gsis("arbitrator")

        # Arbitrator should have access to all major GSIs
        critical_gsis = [
            FLIGHT_NUMBER_DATE_INDEX,
            FLIGHT_ID_INDEX,
            FLIGHT_POSITION_INDEX
        ]

        for gsi in critical_gsis:
            assert gsi in arbitrator_gsis, f"Arbitrator should use {gsi}"


class TestConstantIntegrity:
    """Test constant definitions are complete and consistent."""

    def test_all_agents_defined(self):
        """Test that all expected agents are defined."""
        expected_agents = {
            "crew_compliance",
            "maintenance",
            "regulatory",
            "network",
            "guest_experience",
            "cargo",
            "finance",
            "arbitrator"
        }

        defined_agents = set(AGENT_TABLE_ACCESS.keys())
        assert defined_agents == expected_agents

    def test_all_agents_have_gsi_access(self):
        """Test that all agents have GSI access defined."""
        for agent in AGENT_TABLE_ACCESS.keys():
            assert agent in AGENT_GSI_ACCESS, f"Agent {agent} missing GSI access definition"

    def test_all_agents_have_flight_table_access(self):
        """Test that all agents can access flights table."""
        for agent, tables in AGENT_TABLE_ACCESS.items():
            assert FLIGHTS_TABLE in tables, f"Agent {agent} should access {FLIGHTS_TABLE}"

    def test_all_agents_have_flight_number_date_index(self):
        """Test that all agents can use flight-number-date-index."""
        for agent, gsis in AGENT_GSI_ACCESS.items():
            assert FLIGHT_NUMBER_DATE_INDEX in gsis, \
                f"Agent {agent} should use {FLIGHT_NUMBER_DATE_INDEX}"

    def test_all_tables_list_complete(self):
        """Test that ALL_TABLES list is comprehensive."""
        # Check that key tables are in ALL_TABLES
        key_tables = [
            FLIGHTS_TABLE,
            BOOKINGS_TABLE,
            CREW_ROSTER_TABLE,
            MAINTENANCE_WORK_ORDERS_TABLE
        ]

        for table in key_tables:
            assert table in ALL_TABLES, f"{table} should be in ALL_TABLES"

    def test_all_gsis_list_complete(self):
        """Test that ALL_GSIS list is comprehensive."""
        # Check that key GSIs are in ALL_GSIS
        key_gsis = [
            FLIGHT_NUMBER_DATE_INDEX,
            FLIGHT_ID_INDEX,
            FLIGHT_POSITION_INDEX
        ]

        for gsi in key_gsis:
            assert gsi in ALL_GSIS, f"{gsi} should be in ALL_GSIS"

    def test_no_duplicate_tables(self):
        """Test that ALL_TABLES has no duplicates."""
        assert len(ALL_TABLES) == len(set(ALL_TABLES)), "ALL_TABLES contains duplicates"

    def test_no_duplicate_gsis(self):
        """Test that ALL_GSIS has no duplicates."""
        assert len(ALL_GSIS) == len(set(ALL_GSIS)), "ALL_GSIS contains duplicates"


class TestTableAccessRestrictions:
    """Test that agent table access restrictions are properly enforced."""

    def test_crew_compliance_restricted_tables(self):
        """Test crew compliance cannot access unauthorized tables."""
        crew_tables = get_agent_tables("crew_compliance")

        # Should NOT have access to these tables
        unauthorized = [BOOKINGS_TABLE, MAINTENANCE_WORK_ORDERS_TABLE]

        for table in unauthorized:
            assert table not in crew_tables, \
                f"Crew compliance should not access {table}"

    def test_network_restricted_tables(self):
        """Test network agent has minimal table access."""
        network_tables = get_agent_tables("network")

        # Network should only have 2 tables
        assert len(network_tables) == 2

        # Should NOT have access to passenger or crew data
        unauthorized = [BOOKINGS_TABLE, CREW_ROSTER_TABLE]

        for table in unauthorized:
            assert table not in network_tables, \
                f"Network should not access {table}"

    def test_guest_experience_restricted_tables(self):
        """Test guest experience cannot access crew or maintenance data."""
        guest_tables = get_agent_tables("guest_experience")

        # Should NOT have access to these tables
        unauthorized = [CREW_ROSTER_TABLE, MAINTENANCE_WORK_ORDERS_TABLE]

        for table in unauthorized:
            assert table not in guest_tables, \
                f"Guest experience should not access {table}"


class TestGSIAccessRestrictions:
    """Test that agent GSI access restrictions are properly enforced."""

    def test_network_restricted_gsis(self):
        """Test network agent has limited GSI access."""
        network_gsis = get_agent_gsis("network")

        # Should NOT have access to passenger-related GSIs
        assert FLIGHT_ID_INDEX not in network_gsis, \
            "Network should not use flight-id-index (bookings)"

    def test_cargo_restricted_gsis(self):
        """Test cargo agent has cargo-specific GSI access."""
        cargo_gsis = get_agent_gsis("cargo")

        # Should have cargo-specific GSIs
        assert "flight-loading-index" in cargo_gsis
        assert "shipment-index" in cargo_gsis

        # Should NOT have crew-related GSIs
        assert FLIGHT_POSITION_INDEX not in cargo_gsis, \
            "Cargo should not use flight-position-index (crew)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
