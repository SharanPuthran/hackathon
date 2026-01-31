# Product Overview

SkyMarshal is a multi-agent AI system for airline disruption management built on AWS Bedrock AgentCore. The system analyzes flight disruptions through 7 specialized agents organized in a two-phase execution model (safety → business) to provide comprehensive impact assessments and recovery recommendations.

## Core Capabilities

- **Safety-First Analysis**: Mandatory safety agents (crew compliance, maintenance, regulatory) execute first with binding constraints
- **Business Impact Assessment**: Business agents (network, guest experience, cargo, finance) analyze operational and financial impacts
- **Parallel Processing**: Agents within each phase run concurrently for optimal performance
- **Natural Language Interface**: Accepts disruption descriptions in plain English
- **DynamoDB Integration**: Real-time access to operational data (flights, passengers, crew, cargo)
- **Explainable Decisions**: All assessments include clear rationale and confidence scores

## Key Principles

1. Safety constraints are non-negotiable and must be satisfied before business analysis
2. All agents use chain-of-thought reasoning for transparent decision-making
3. Human-in-the-loop approval required for critical decisions
4. Complete audit trails for regulatory compliance
5. Conservative fallbacks when data is incomplete or agents timeout
