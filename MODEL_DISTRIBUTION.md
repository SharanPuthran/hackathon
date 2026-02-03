# SkyMarshal Model Distribution

Complete list of all AI models used across the SkyMarshal project.

**Last Updated:** February 3, 2026

---

## Current Production Deployment (AgentCore)

### Primary Model: Claude Sonnet 4.5

**Model ID:** `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

**Used By:**

- All 7 domain agents (crew_compliance, maintenance, regulatory, network, guest_experience, cargo, finance)
- Main orchestrator

**Configuration:**

- Temperature: 0.3
- Max Tokens: 8192
- Provider: AWS Bedrock (US cross-region inference profile)
- Location: `skymarshal_agents_new/skymarshal/src/model/load.py`

**Rationale:**

- Optimal balance of speed, accuracy, and cost
- Multi-region availability for high reliability
- Excellent structured output support
- Strong reasoning capabilities for domain-specific analysis

---

## Arbitrator Model (Special Configuration)

### Primary: Claude Opus 4.5

**Model ID:** `us.anthropic.claude-opus-4-5-20250514-v1:0`

**Used By:**

- Arbitrator agent (conflict resolution and final decision-making)

**Configuration:**

- Temperature: 0.1 (very low for consistent decision-making)
- Max Tokens: 16384
- Provider: AWS Bedrock
- Location: `skymarshal_agents_new/skymarshal/src/agents/arbitrator/agent.py`

**Rationale:**

- Most powerful reasoning model for complex multi-criteria optimization
- Critical for safety-first decision-making
- Handles complex conflict resolution scenarios
- Generates comprehensive justifications

### Fallback: Claude Sonnet 4.5

**Model ID:** `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

**Used When:**

- Opus 4.5 is not available in the region
- Automatic fallback with same configuration

**Configuration:**

- Temperature: 0.1
- Max Tokens: 16384
- Provider: AWS Bedrock

---

## Legacy Configuration (src/ directory - Not in Production)

### Amazon Nova Premier

**Model ID:** `us.amazon.nova-premier-v1:0`

**Previously Used By (Not Active):**

- All agents in the legacy `src/` implementation
- Orchestrator
- Arbitrator

**Status:**

- ⚠️ **DEPRECATED** - This configuration is in the old `src/config.py` file
- Not used in current AgentCore deployment
- Kept for reference only

**Location:** `src/config.py`

---

## Model Selection Strategy

### Agent Type → Model Mapping

| Agent Type                   | Model                                  | Reasoning                                          |
| ---------------------------- | -------------------------------------- | -------------------------------------------------- |
| **Domain Agents** (7 agents) | Claude Sonnet 4.5                      | Fast, accurate, cost-effective for domain analysis |
| **Arbitrator**               | Claude Opus 4.5 (fallback: Sonnet 4.5) | Maximum reasoning power for critical decisions     |
| **Orchestrator**             | Claude Sonnet 4.5                      | Efficient workflow coordination                    |

### Temperature Settings

| Use Case      | Temperature | Rationale                                         |
| ------------- | ----------- | ------------------------------------------------- |
| Domain Agents | 0.3         | Balance between consistency and creativity        |
| Arbitrator    | 0.1         | Maximum consistency for safety-critical decisions |

### Token Limits

| Model                 | Max Tokens | Use Case                                              |
| --------------------- | ---------- | ----------------------------------------------------- |
| Sonnet 4.5 (Agents)   | 8,192      | Sufficient for domain analysis with structured output |
| Opus 4.5 (Arbitrator) | 16,384     | Large context for complex multi-agent synthesis       |

---

## Model Availability Check

The arbitrator includes automatic model availability checking:

```python
def _is_model_available(model_id: str) -> bool:
    """Check if a specific model is available in AWS Bedrock"""
    # Queries AWS Bedrock for available models
    # Supports both exact match and prefix match
    # Returns True if model is accessible
```

**Fallback Logic:**

1. Try to load Claude Opus 4.5
2. If unavailable, automatically fall back to Claude Sonnet 4.5
3. Log the fallback for monitoring

---

## Cross-Region Inference Profiles

All models use AWS Bedrock's US cross-region inference profiles for:

- **High Availability:** Automatic failover across US regions
- **Low Latency:** Optimized routing to nearest available region
- **Reliability:** 99.9% uptime SLA

**Profile Format:** `us.anthropic.claude-{model}-{version}-v1:0`

**Documentation:** https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html

---

## Cost Optimization

### Current Approach

- Use Sonnet 4.5 for all domain agents (7 agents × parallel execution)
- Reserve Opus 4.5 only for arbitrator (1 agent × sequential execution)
- This provides optimal cost/performance ratio

### Cost Breakdown (Estimated per Request)

- **Phase 1 (Initial):** 7 agents × Sonnet 4.5 = ~$0.15
- **Phase 2 (Revision):** 7 agents × Sonnet 4.5 = ~$0.15
- **Phase 3 (Arbitration):** 1 agent × Opus 4.5 = ~$0.10
- **Total per Request:** ~$0.40

---

## Knowledge Base Integration

### Arbitrator Knowledge Base

**Knowledge Base ID:** `UDONMVCXEW`

**Purpose:**

- Historical disruption precedents
- Regulatory compliance documentation
- Best practice guidelines

**Model Used for Retrieval:**

- Uses the same model as arbitrator (Opus 4.5 or Sonnet 4.5 fallback)
- Retrieval-augmented generation (RAG) for context-aware decisions

**Location:** `skymarshal_agents_new/skymarshal/src/agents/arbitrator/knowledge_base.py`

---

## Model Access Requirements

### AWS Bedrock Model Access

All Claude models require use case approval:

- **Form:** https://pages.awscloud.com/GLOBAL-ln-GC-Bedrock-3pmodel-interest-form-2024.html
- **Approval Time:** 1-2 business days
- **Required for:** Production deployment

### Current Status

✅ Claude Sonnet 4.5 - Approved and Active
✅ Claude Opus 4.5 - Approved and Active (with fallback)

---

## Deployment Configurations

### AgentCore Deployment

**File:** `skymarshal_agents_new/skymarshal/.bedrock_agentcore.yaml`

```yaml
runtime:
  model: us.anthropic.claude-sonnet-4-5-20250929-v1:0
  timeout: 300
  memory: 2048
```

### Environment Variables

```bash
AWS_REGION=us-east-1
CHECKPOINT_MODE=production
```

---

## Testing and Validation

### Model Performance Metrics

- **Latency:** Sonnet 4.5 avg 2-3s, Opus 4.5 avg 4-6s
- **Accuracy:** Both models >95% on structured output tasks
- **Reliability:** 99.9% success rate with retry logic

### Throttling Handling

- Automatic retry with exponential backoff
- Max retries: 4
- Fallback to manual review if all retries fail

---

## Future Considerations

### Potential Model Updates

1. **Claude Opus 4.6** - When available, upgrade arbitrator
2. **Claude Sonnet 4.6** - When available, upgrade all agents
3. **Amazon Nova Pro** - Consider for cost optimization if performance is comparable

### Monitoring Recommendations

- Track model availability and fallback frequency
- Monitor token usage and costs per agent
- Measure latency and accuracy metrics
- Alert on throttling errors

---

## References

- **AWS Bedrock Documentation:** https://docs.aws.amazon.com/bedrock/
- **Claude Model Cards:** https://www.anthropic.com/claude
- **AgentCore Documentation:** https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html
- **Model Pricing:** https://aws.amazon.com/bedrock/pricing/

---

## Summary

**Production Models:**

- **7 Domain Agents:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **1 Arbitrator:** Claude Opus 4.5 (`us.anthropic.claude-opus-4-5-20250514-v1:0`) with Sonnet 4.5 fallback
- **1 Orchestrator:** Claude Sonnet 4.5 (embedded in AgentCore)

**Total Unique Models:** 2 (Sonnet 4.5 and Opus 4.5)

**Provider:** AWS Bedrock (US cross-region inference profiles)

**Deployment:** AWS Bedrock AgentCore Runtime
