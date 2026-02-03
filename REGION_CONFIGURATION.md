# Region Configuration

## Current Setup

### Bedrock (Model Invocations)

- **Region**: eu-west-1
- **Reason**: Lower latency from Europe, better availability
- **Models**: Global CRIS endpoints (route automatically to best region)
  - `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
  - `global.anthropic.claude-haiku-4-5-20251001-v1:0`
  - `global.anthropic.claude-opus-4-5-20251101-v1:0`

### DynamoDB (Operational Data)

- **Region**: us-east-1
- **Reason**: Global CRIS (Cross-Region Inference Service) data location
- **Tables**: flights, bookings, passengers, crew, cargo, etc.

## Benefits

1. **Lower Latency**: eu-west-1 Bedrock endpoints provide faster response times from Europe
2. **Global CRIS**: Model endpoints automatically route to best available region
3. **Data Consistency**: DynamoDB remains in us-east-1 for global data access
4. **High Availability**: Global CRIS provides automatic failover across regions

## Configuration Files

- `skymarshal_agents_new/skymarshal/src/model/load.py` - Bedrock region configuration
- `skymarshal_agents_new/skymarshal/src/database/dynamodb.py` - DynamoDB region (us-east-1)

## Testing

To verify the configuration:

```bash
cd skymarshal_agents_new/skymarshal
uv run agentcore dev
```

The logs will show:

- `Loading model in eu-west-1...` for Bedrock
- DynamoDB connections to us-east-1

## Rollback

To revert to us-east-1 for Bedrock, change in `src/model/load.py`:

```python
BEDROCK_REGION = "us-east-1"  # Change back to us-east-1
```
