# Quick Start Guide

## Current Status

✅ Stage 1 Complete:

- Project structure initialized
- Dependencies consolidated in `skymarshal/pyproject.toml`
- Basic directory structure created
- Root-level Python files removed

## Working Directory

**Always work from the `skymarshal/` directory:**

```bash
cd skymarshal_agents_new/skymarshal
```

## Common Commands

### Dependency Management

```bash
# Sync dependencies (install/update)
uv sync

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update dependencies
uv lock --upgrade
```

### Code Quality

```bash
# Check code with ruff
uv run ruff check src/

# Format code with ruff
uv run ruff format src/

# Fix auto-fixable issues
uv run ruff check --fix src/
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest test/test_main.py

# Run with coverage
uv run pytest --cov=src
```

### AgentCore Development

```bash
# Start development server
uv run agentcore dev

# Deploy to AgentCore
uv run agentcore deploy

# Configure agent
uv run agentcore configure
```

### Python REPL

```bash
# Start Python REPL with project dependencies
uv run python3

# Test imports
uv run python3 -c "from database import DynamoDBClient"
```

## Next Steps (Stage 2)

1. Migrate database layer to `src/database/`
2. Migrate MCP client to `src/mcp_client/`
3. Migrate model utilities to `src/model/`
4. Migrate response utilities to `src/utils/`
5. Validate with ruff and test imports

## File Paths Reference

When the spec says "Copy X to src/Y", the actual path is:

```
skymarshal_agents_new/skymarshal/src/Y
```

**Example:**

- Spec: "Copy database/dynamodb.py to src/database/dynamodb.py"
- Actual: `skymarshal_agents_new/skymarshal/src/database/dynamodb.py`

## Directory Structure

```
skymarshal/                    ← YOU ARE HERE (working directory)
├── pyproject.toml             ← Dependencies
├── uv.lock                    ← Lock file
├── .bedrock_agentcore.yaml    ← AgentCore config
└── src/                       ← Source code
    ├── agents/                ← Agent modules (to be migrated)
    ├── database/              ← Database layer (to be migrated)
    ├── mcp_client/            ← MCP client (to be migrated)
    ├── model/                 ← Model utilities (to be migrated)
    └── utils/                 ← Shared utilities (to be migrated)
```

## Troubleshooting

### Import errors

Make sure you're in the `skymarshal/` directory and have run `uv sync`.

### Command not found

Use `uv run` prefix for all Python commands:

```bash
# ❌ Wrong
python3 script.py

# ✅ Correct
uv run python3 script.py
```

### Ruff errors

Run `uv run ruff check --fix src/` to auto-fix issues.

### AgentCore errors

Check `.bedrock_agentcore.yaml` configuration and ensure AWS credentials are set.
