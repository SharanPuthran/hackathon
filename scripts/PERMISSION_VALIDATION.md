# Permission Validation Documentation

## Overview

The DynamoDB validation script now includes comprehensive IAM permission validation to ensure that AgentCore agents have the necessary permissions to access DynamoDB tables.

## Features

### 1. Execution Role Detection

The script automatically detects the AgentCore execution role from:

1. **Environment Variable**: `AGENTCORE_EXECUTION_ROLE`
2. **Config File**: `.bedrock_agentcore.yaml` (requires PyYAML)

Example:

```bash
# Set via environment variable
export AGENTCORE_EXECUTION_ROLE="arn:aws:iam::123456789012:role/MyAgentRole"
python scripts/validate_dynamodb_data.py
```

### 2. IAM Role Validation

The script validates:

- **Role Existence**: Checks if the IAM role exists
- **Inline Policies**: Retrieves and analyzes inline policies attached to the role
- **Managed Policies**: Retrieves and analyzes managed policies attached to the role

### 3. DynamoDB Permission Checks

The script verifies that the role has the following DynamoDB permissions:

- `dynamodb:Query` - Required for querying tables using GSIs
- `dynamodb:Scan` - Required for scanning tables
- `dynamodb:GetItem` - Required for retrieving individual items
- `dynamodb:BatchGetItem` - Required for batch operations
- `dynamodb:DescribeTable` - Required for table metadata

### 4. Agent-Specific Table Access

The script validates that agents have access to their required tables based on the `AGENT_TABLE_ACCESS` configuration:

| Agent            | Required Tables                                                                           |
| ---------------- | ----------------------------------------------------------------------------------------- |
| crew_compliance  | Flights, CrewRoster, CrewMembers                                                          |
| maintenance      | Flights, MaintenanceWorkOrders, MaintenanceStaff, MaintenanceRoster, AircraftAvailability |
| regulatory       | Flights, CrewRoster, MaintenanceWorkOrders, Weather                                       |
| network          | Flights, AircraftAvailability                                                             |
| guest_experience | Flights, Bookings, Baggage                                                                |
| cargo            | Flights, CargoFlightAssignments, CargoShipments                                           |
| finance          | Flights, Bookings, CargoFlightAssignments, MaintenanceWorkOrders                          |
| arbitrator       | All tables (comprehensive access)                                                         |

## Usage

### Basic Usage

```bash
python scripts/validate_dynamodb_data.py
```

### With Custom Output File

```bash
python scripts/validate_dynamodb_data.py --output my_report.json
```

### With Custom Region

```bash
python scripts/validate_dynamodb_data.py --region us-west-2
```

### With Environment Variable

```bash
export AGENTCORE_EXECUTION_ROLE="arn:aws:iam::123456789012:role/MyRole"
python scripts/validate_dynamodb_data.py
```

## Validation Report

The validation report includes:

### Permission Issues

```json
{
  "issues": {
    "by_type": {
      "role_exists": [...],
      "dynamodb_permissions_ok": [...],
      "table_access_ok": [...],
      "missing_dynamodb_permissions": [...],
      "missing_table_access": [...],
      "agent_table_access_incomplete": [...]
    }
  }
}
```

### Issue Severities

- **error**: Critical issues that must be fixed (e.g., role doesn't exist, no DynamoDB permissions)
- **warning**: Issues that should be addressed (e.g., missing specific permissions, incomplete table access)
- **info**: Informational messages (e.g., role exists, permissions OK)

## Example Output

```
============================================================
Validating agent permissions...
  Checking role: AmazonBedrockAgentCoreSDKRuntime-us-east-1-51e75bb8e1
  ✓ IAM role exists
  ✓ Role has required DynamoDB permissions
  ✓ Role has wildcard access to DynamoDB tables
  ✓ Agent 'crew_compliance' has access to all required tables (3 tables)
  ✓ Agent 'maintenance' has access to all required tables (5 tables)
  ✓ Agent 'regulatory' has access to all required tables (4 tables)
  ✓ Agent 'network' has access to all required tables (2 tables)
  ✓ Agent 'guest_experience' has access to all required tables (3 tables)
  ✓ Agent 'cargo' has access to all required tables (3 tables)
  ✓ Agent 'finance' has access to all required tables (4 tables)
  ✓ Agent 'arbitrator' has access to all required tables (13 tables)
============================================================
```

## Troubleshooting

### Role Not Found

**Issue**: `Could not determine AgentCore execution role ARN`

**Solution**:

1. Set the `AGENTCORE_EXECUTION_ROLE` environment variable
2. Ensure `.bedrock_agentcore.yaml` exists and contains the execution role
3. Install PyYAML: `pip install pyyaml`

### Missing DynamoDB Permissions

**Issue**: `Role has no DynamoDB permissions`

**Solution**: Add DynamoDB permissions to the IAM role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:GetItem",
        "dynamodb:BatchGetItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": "*"
    }
  ]
}
```

### Missing Table Access

**Issue**: `Agent 'crew_compliance' may not have access to tables: CrewRoster`

**Solution**: Update the IAM policy to grant access to specific tables:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem"],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/Flights",
        "arn:aws:dynamodb:us-east-1:123456789012:table/CrewRoster",
        "arn:aws:dynamodb:us-east-1:123456789012:table/CrewMembers"
      ]
    }
  ]
}
```

## Testing

Run the test suite to verify permission validation functionality:

```bash
python scripts/test_permission_validation.py
```

Expected output:

```
============================================================
Testing Permission Validation Functionality
============================================================
Testing AGENT_TABLE_ACCESS constants...
  ✓ All 8 agents defined
  ✓ All agents have access to Flights table
Testing _get_agentcore_execution_role...
  ✓ Environment variable test passed
  ✓ Config file test passed
Testing _validate_role_exists...
  ✓ Role exists test passed
  ✓ Role doesn't exist test passed
Testing _get_inline_policies...
  ✓ Inline policies test passed
Testing _validate_dynamodb_permissions...
  ✓ Full permissions test passed
  ✓ No permissions test passed
Testing _validate_agent_table_access_permissions...
  ✓ Wildcard access test passed
  ✓ Specific table access test passed
============================================================
All tests passed! ✓
============================================================
```

## Integration with CI/CD

Add permission validation to your CI/CD pipeline:

```yaml
# .github/workflows/validate.yml
name: Validate DynamoDB

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Install dependencies
        run: pip install boto3 pyyaml
      - name: Run validation
        run: python scripts/validate_dynamodb_data.py
```

## Best Practices

1. **Least Privilege**: Grant only the minimum permissions required for each agent
2. **Regular Validation**: Run validation script regularly to catch permission drift
3. **Environment Variables**: Use environment variables for sensitive role ARNs in CI/CD
4. **Monitoring**: Set up alerts for permission validation failures
5. **Documentation**: Keep agent table access requirements up to date in `database/constants.py`

## Related Files

- `scripts/validate_dynamodb_data.py` - Main validation script
- `scripts/test_permission_validation.py` - Test suite
- `skymarshal_agents_new/skymarshal/src/database/constants.py` - Agent table access configuration
- `.bedrock_agentcore.yaml` - AgentCore configuration with execution role
