# Migration Structure Update

## Changes Made

### 1. Consolidated Dependencies

All dependencies have been consolidated into `skymarshal/pyproject.toml`:

- bedrock-agentcore >= 1.2.0
- bedrock-agentcore-starter-toolkit >= 0.2.8
- langchain >= 1.2.7
- langchain-aws >= 1.2.2
- langchain-mcp-adapters >= 0.2.1
- langgraph >= 1.0.7
- mcp >= 1.26.0
- python-dotenv >= 1.2.1
- tiktoken >= 0.11.0
- aws-opentelemetry-distro >= 0.10.0

Dev dependencies:

- hypothesis >= 6.151.4
- pytest >= 9.0.2
- pytest-asyncio >= 1.3.0

### 2. Removed Root-Level Python Files

The following files have been removed from `skymarshal_agents_new/` root:

- `pyproject.toml` (consolidated into skymarshal/)
- `uv.lock` (consolidated into skymarshal/)
- `.python-version` (not needed at root)
- `main.py` (not needed at root)

### 3. Updated Project Structure

```
skymarshal_agents_new/
├── README.md                      # Project overview
└── skymarshal/                    # Main agent module (Python package)
    ├── pyproject.toml             # UV-managed dependencies
    ├── uv.lock                    # Dependency lock file
    ├── .bedrock_agentcore.yaml    # AgentCore configuration
    └── src/                       # Source code
        ├── main.py                # Orchestrator entrypoint
        ├── agents/                # Agent modules
        ├── database/              # Database integration
        ├── mcp_client/            # MCP client
        ├── model/                 # Model utilities
        └── utils/                 # Shared utilities
```

### 4. Path Updates for Migration Tasks

All migration tasks should now target `skymarshal/src/` instead of just `src/`:

**Examples:**

- OLD: `Copy database/dynamodb.py to src/database/dynamodb.py`
- NEW: `Copy database/dynamodb.py to skymarshal/src/database/dynamodb.py`

- OLD: `Run uv run ruff check src/`
- NEW: `Run uv run ruff check src/` (from skymarshal/ directory)

### 5. Working Directory

All UV commands should be run from the `skymarshal/` directory:

```bash
cd skymarshal_agents_new/skymarshal
uv sync
uv run ruff check src/
uv run agentcore dev
```

## Rationale

This structure ensures that:

1. The `skymarshal/` directory is the actual Python package/agent
2. Dependencies are managed in one place
3. The root `skymarshal_agents_new/` directory is just a container
4. The `src/` directory at root is temporary for migration reference
5. All development and deployment happens within `skymarshal/`
