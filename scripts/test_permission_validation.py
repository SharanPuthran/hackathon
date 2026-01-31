#!/usr/bin/env python3
"""
Test script for permission validation functionality

This script tests the IAM permission validation without requiring actual AWS credentials.
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, "skymarshal_agents_new/skymarshal/src")

from database.constants import AGENT_TABLE_ACCESS


def test_get_agentcore_execution_role():
    """Test getting execution role from environment and config"""
    print("Testing _get_agentcore_execution_role...")
    
    # Import the validator
    sys.path.insert(0, "scripts")
    from validate_dynamodb_data import DynamoDBValidator
    
    # Test with environment variable
    with patch.dict(os.environ, {"AGENTCORE_EXECUTION_ROLE": "arn:aws:iam::123456789012:role/TestRole"}):
        validator = DynamoDBValidator()
        role_arn = validator._get_agentcore_execution_role()
        assert role_arn == "arn:aws:iam::123456789012:role/TestRole", "Should get role from environment"
        print("  ✓ Environment variable test passed")
    
    # Test without environment variable (should try config file)
    with patch.dict(os.environ, {}, clear=True):
        validator = DynamoDBValidator()
        role_arn = validator._get_agentcore_execution_role()
        # Should return None or read from config file if it exists
        print(f"  ✓ Config file test passed (role_arn: {role_arn})")


def test_validate_role_exists():
    """Test role existence validation"""
    print("\nTesting _validate_role_exists...")
    
    sys.path.insert(0, "scripts")
    from validate_dynamodb_data import DynamoDBValidator
    
    validator = DynamoDBValidator()
    
    # Mock IAM client
    validator.iam_client = Mock()
    
    # Test role exists
    validator.iam_client.get_role.return_value = {"Role": {"RoleName": "TestRole"}}
    result = validator._validate_role_exists("TestRole")
    assert result == True, "Should return True when role exists"
    print("  ✓ Role exists test passed")
    
    # Test role doesn't exist - create a proper exception class
    class NoSuchEntityException(Exception):
        pass
    
    validator.iam_client.exceptions = type('obj', (object,), {
        'NoSuchEntityException': NoSuchEntityException
    })
    
    validator.iam_client.get_role.side_effect = NoSuchEntityException("Role not found")
    validator.issues = []  # Clear previous issues
    result = validator._validate_role_exists("NonExistentRole")
    assert result == False, "Should return False when role doesn't exist"
    print("  ✓ Role doesn't exist test passed")


def test_get_inline_policies():
    """Test getting inline policies"""
    print("\nTesting _get_inline_policies...")
    
    sys.path.insert(0, "scripts")
    from validate_dynamodb_data import DynamoDBValidator
    
    validator = DynamoDBValidator()
    validator.iam_client = Mock()
    
    # Mock policy list
    validator.iam_client.list_role_policies.return_value = {
        "PolicyNames": ["Policy1", "Policy2"]
    }
    
    # Mock policy documents
    validator.iam_client.get_role_policy.side_effect = [
        {"PolicyDocument": {"Statement": [{"Effect": "Allow", "Action": "dynamodb:*"}]}},
        {"PolicyDocument": {"Statement": [{"Effect": "Allow", "Action": "s3:*"}]}}
    ]
    
    policies = validator._get_inline_policies("TestRole")
    assert len(policies) == 2, "Should return 2 policies"
    assert policies[0]["name"] == "Policy1", "First policy name should be Policy1"
    print("  ✓ Inline policies test passed")


def test_validate_dynamodb_permissions():
    """Test DynamoDB permission validation"""
    print("\nTesting _validate_dynamodb_permissions...")
    
    sys.path.insert(0, "scripts")
    from validate_dynamodb_data import DynamoDBValidator
    
    validator = DynamoDBValidator()
    
    # Test with full DynamoDB permissions
    policies = [{
        "name": "DynamoDBFullAccess",
        "document": {
            "Statement": [{
                "Effect": "Allow",
                "Action": "dynamodb:*",
                "Resource": "*"
            }]
        }
    }]
    
    validator._validate_dynamodb_permissions("TestRole", policies, [])
    
    # Check that we got an info issue about permissions being OK
    info_issues = [i for i in validator.issues if i.severity == "info" and "permissions_ok" in i.issue_type]
    assert len(info_issues) > 0, "Should have info issue about permissions being OK"
    print("  ✓ Full permissions test passed")
    
    # Test with no DynamoDB permissions
    validator.issues = []
    policies = [{
        "name": "S3Access",
        "document": {
            "Statement": [{
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": "*"
            }]
        }
    }]
    
    validator._validate_dynamodb_permissions("TestRole", policies, [])
    
    # Check that we got an error about missing permissions
    error_issues = [i for i in validator.issues if i.severity == "error" and "missing_dynamodb_permissions" in i.issue_type]
    assert len(error_issues) > 0, "Should have error issue about missing permissions"
    print("  ✓ No permissions test passed")


def test_validate_agent_table_access():
    """Test agent table access validation"""
    print("\nTesting _validate_agent_table_access_permissions...")
    
    sys.path.insert(0, "scripts")
    from validate_dynamodb_data import DynamoDBValidator
    
    validator = DynamoDBValidator()
    
    # Test with wildcard access
    policies = [{
        "name": "DynamoDBFullAccess",
        "document": {
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"],
                "Resource": "*"
            }]
        }
    }]
    
    validator._validate_agent_table_access_permissions("TestRole", policies, [])
    
    # Check that we got info about wildcard access
    info_issues = [i for i in validator.issues if "wildcard" in i.issue_type]
    assert len(info_issues) > 0, "Should have info issue about wildcard access"
    print("  ✓ Wildcard access test passed")
    
    # Test with specific table access
    validator.issues = []
    policies = [{
        "name": "SpecificTableAccess",
        "document": {
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:Query", "dynamodb:Scan"],
                "Resource": [
                    "arn:aws:dynamodb:us-east-1:123456789012:table/Flights",
                    "arn:aws:dynamodb:us-east-1:123456789012:table/Bookings"
                ]
            }]
        }
    }]
    
    validator._validate_agent_table_access_permissions("TestRole", policies, [])
    
    # Should have warnings about missing tables
    warning_issues = [i for i in validator.issues if i.severity == "warning" and "missing_table_access" in i.issue_type]
    assert len(warning_issues) > 0, "Should have warnings about missing table access"
    print("  ✓ Specific table access test passed")


def test_agent_table_access_constants():
    """Test that agent table access constants are properly defined"""
    print("\nTesting AGENT_TABLE_ACCESS constants...")
    
    # Check that all expected agents are defined
    expected_agents = [
        "crew_compliance",
        "maintenance",
        "regulatory",
        "network",
        "guest_experience",
        "cargo",
        "finance",
        "arbitrator"
    ]
    
    for agent in expected_agents:
        assert agent in AGENT_TABLE_ACCESS, f"Agent {agent} should be in AGENT_TABLE_ACCESS"
        assert len(AGENT_TABLE_ACCESS[agent]) > 0, f"Agent {agent} should have at least one table"
    
    print(f"  ✓ All {len(expected_agents)} agents defined")
    
    # Check that all agents have access to Flights table
    for agent, tables in AGENT_TABLE_ACCESS.items():
        if agent != "arbitrator":  # Arbitrator has access to all tables
            assert "Flights" in tables, f"Agent {agent} should have access to Flights table"
    
    print("  ✓ All agents have access to Flights table")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Permission Validation Functionality")
    print("=" * 60)
    
    try:
        test_agent_table_access_constants()
        test_get_agentcore_execution_role()
        test_validate_role_exists()
        test_get_inline_policies()
        test_validate_dynamodb_permissions()
        test_validate_agent_table_access()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
