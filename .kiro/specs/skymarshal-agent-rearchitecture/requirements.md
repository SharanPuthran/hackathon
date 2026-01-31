# Requirements Document

## Introduction

This document specifies the requirements for rearchitecting the SkyMarshal agents system from its current structure to a new architecture based on the bedrock-agentcore-starter-toolkit. The rearchitecture aims to modernize the agent structure, improve maintainability through modular design, and ensure compatibility with AWS Bedrock AgentCore deployment while maintaining all existing functionality.

## Glossary

- **Agent**: A specialized AI component that analyzes specific aspects of flight disruptions (e.g., crew compliance, maintenance, regulatory)
- **Orchestrator**: The main coordination component that routes requests to appropriate agents and aggregates responses
- **Safety_Agent**: An agent responsible for safety-critical assessments (crew compliance, maintenance, regulatory)
- **Business_Agent**: An agent responsible for business impact assessments (network, guest experience, cargo, finance)
- **MCP_Client**: Model Context Protocol client for external tool integration
- **Database_Layer**: DynamoDB integration layer providing data access tools for agents
- **AgentCore**: AWS Bedrock AgentCore runtime platform for deploying and running agents
- **UV**: Python package and environment manager (replacement for pip/virtualenv)
- **Ruff**: Fast Python linter and code formatter
- **Module**: A self-contained Python package in a separate directory that can be imported

## Requirements

### Requirement 1: Project Initialization

**User Story:** As a developer, I want to initialize a new agent project using modern Python tooling, so that I have a clean foundation for the rearchitected system.

#### Acceptance Criteria

1. WHEN initializing the project, THE System SHALL use uv to create the project structure in the skymarshal/ subdirectory
2. THE System SHALL add bedrock-agentcore-starter-toolkit as a dependency
3. THE System SHALL configure the project to use python3 as the runtime binary
4. THE System SHALL initialize AgentCore runtime configuration in the skymarshal/ directory
5. THE System SHALL use uv and uvx for all environment management operations from the skymarshal/ directory

### Requirement 2: Agent Modularization

**User Story:** As a developer, I want each agent to be a separate importable Python module, so that the codebase is maintainable and agents can be developed independently.

#### Acceptance Criteria

1. WHEN structuring agents, THE System SHALL define each agent as a separate Python module in its own directory
2. THE System SHALL ensure each agent module can be imported into main.py
3. THE System SHALL maintain seven distinct agent modules: crew_compliance, maintenance, regulatory, network, guest_experience, cargo, and finance
4. WHEN organizing agents, THE System SHALL preserve the distinction between safety agents and business agents
5. THE System SHALL ensure each agent module exports its analysis function

### Requirement 3: Functionality Migration

**User Story:** As a developer, I want all existing functionality migrated to the new structure, so that no capabilities are lost during rearchitecture.

#### Acceptance Criteria

1. WHEN migrating agents, THE System SHALL preserve all seven agent implementations from skymarshal_agents/src/agents/
2. THE System SHALL migrate the database integration layer from src/database/
3. THE System SHALL migrate the MCP client integration from src/mcp_client/
4. THE System SHALL migrate model loading utilities from src/model/
5. THE System SHALL migrate response aggregation utilities from src/utils/
6. THE System SHALL preserve the orchestrator routing logic from src/main.py
7. THE System SHALL maintain compatibility with bedrock-agentcore >= 1.0.3, langchain (for tools), langgraph (for orchestration), and mcp dependencies

### Requirement 4: Code Quality Validation

**User Story:** As a developer, I want code to be validated at each migration stage, so that I can catch errors early and maintain code quality.

#### Acceptance Criteria

1. WHEN completing each migration stage, THE System SHALL run ruff linting on the migrated code
2. IF ruff identifies issues, THEN THE System SHALL fix the issues before proceeding
3. THE System SHALL ensure all migrated code passes ruff checks with no errors
4. THE System SHALL use ruff for both linting and formatting validation

### Requirement 5: Local Testing and Validation

**User Story:** As a developer, I want to test the agent locally after each migration stage, so that I can verify functionality before proceeding.

#### Acceptance Criteria

1. WHEN completing each migration stage, THE System SHALL use agentcore to run the agent in development mode
2. THE System SHALL invoke the agent locally to verify functionality
3. THE System SHALL use "uv run" to execute agentcore commands
4. THE System SHALL verify that the agent responds correctly to test invocations
5. IF local testing fails, THEN THE System SHALL identify and fix issues before proceeding

### Requirement 6: Environment Management

**User Story:** As a developer, I want to use modern Python tooling for environment management, so that dependency management is fast and reliable.

#### Acceptance Criteria

1. THE System SHALL use uv for all package installation operations
2. THE System SHALL use uvx for running command-line tools
3. THE System SHALL NOT use pip for package management
4. THE System SHALL NOT use python directly for execution (use python3 instead)
5. WHEN managing dependencies, THE System SHALL use uv's lock file mechanism

### Requirement 7: Orchestration Preservation

**User Story:** As a developer, I want the orchestration logic preserved, so that multi-agent coordination continues to work correctly.

#### Acceptance Criteria

1. THE System SHALL preserve the agent registry for routing requests
2. THE System SHALL maintain the two-phase execution model (safety agents first, then business agents)
3. THE System SHALL preserve parallel execution of agents within each phase
4. THE System SHALL maintain the response aggregation logic
5. THE System SHALL preserve timeout and error handling for agent execution
6. THE System SHALL maintain the entrypoint decorator pattern for AgentCore integration

### Requirement 8: Database Integration Preservation

**User Story:** As a developer, I want database integration preserved, so that agents can access operational data.

#### Acceptance Criteria

1. THE System SHALL migrate the DynamoDB client implementation
2. THE System SHALL preserve all database tool factories for each agent type
3. THE System SHALL maintain the tool registration mechanism for LangGraph integration (using LangChain Tool format)
4. WHEN agents execute, THE System SHALL provide database tools alongside MCP tools
5. THE System SHALL preserve all database query functions and their signatures

### Requirement 9: AWS Bedrock Compatibility

**User Story:** As a developer, I want the rearchitected system to be compatible with AWS Bedrock AgentCore, so that deployment to production is seamless.

#### Acceptance Criteria

1. THE System SHALL maintain the .bedrock_agentcore.yaml configuration structure
2. THE System SHALL preserve the BedrockAgentCoreApp initialization pattern
3. THE System SHALL maintain the @app.entrypoint decorator usage
4. THE System SHALL ensure the agent can be deployed using AgentCore CLI
5. THE System SHALL preserve all AWS-specific configuration (region, account, execution role)

### Requirement 10: Incremental Migration Strategy

**User Story:** As a developer, I want to migrate functionality incrementally, so that I can validate each step and minimize risk.

#### Acceptance Criteria

1. WHEN migrating, THE System SHALL follow a staged approach: initialization → core structure → agent migration → integration → testing
2. WHEN completing each stage, THE System SHALL validate code quality with ruff
3. WHEN completing each stage, THE System SHALL test functionality locally with agentcore
4. THE System SHALL NOT proceed to the next stage until the current stage is validated
5. IF issues are found, THEN THE System SHALL fix them before proceeding

### Requirement 11: Documentation Updates

**User Story:** As a developer, I want documentation updated for the new structure, so that future developers can understand and maintain the system.

#### Acceptance Criteria

1. WHEN rearchitecture is complete, THE System SHALL update README.md with new structure information
2. THE System SHALL document the module organization and import patterns
3. THE System SHALL document the uv-based workflow for development
4. THE System SHALL document how to run agents locally using agentcore
5. THE System SHALL document the deployment process for AWS Bedrock AgentCore

### Requirement 12: Agent System Prompt Preservation

**User Story:** As a developer, I want all agent system prompts preserved exactly, so that agent behavior remains consistent.

#### Acceptance Criteria

1. WHEN migrating agents, THE System SHALL preserve each agent's complete system prompt
2. THE System SHALL maintain all regulatory frameworks, calculation rules, and output formats defined in prompts
3. THE System SHALL preserve all chain-of-thought analysis processes
4. THE System SHALL maintain all example scenarios and audit trail requirements
5. THE System SHALL ensure no modifications to agent reasoning logic during migration

### Requirement 13: Best Practices Validation

**User Story:** As a developer, I want migrated code validated against Python, AgentCore, and LangGraph best practices, so that the codebase follows framework standards and industry conventions.

#### Acceptance Criteria

1. WHEN migrating any code or agent, THE System SHALL validate the code against Python best practices (PEP 8, type hints, docstrings, async/await patterns)
2. WHEN migrating any code or agent, THE System SHALL fetch and reference official AgentCore documentation from online sources
3. WHEN migrating any code or agent, THE System SHALL fetch and reference official LangGraph documentation from online sources
4. WHEN migrating any code or agent, THE System SHALL validate the code against AgentCore best practices from the fetched official documentation
5. WHEN migrating any code or agent, THE System SHALL validate the code against LangGraph best practices from the fetched official documentation
6. WHEN validation identifies deviations from best practices, THE System SHALL document the findings with specific references to official documentation
7. WHERE improvements can be implemented without breaking functionality, THE System SHALL apply best practice improvements
8. THE System SHALL prioritize framework-specific patterns over generic patterns where applicable
9. THE System SHALL verify that documentation sources are official (langchain-ai.github.io for LangGraph, AWS documentation for AgentCore)
