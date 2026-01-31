# Technology Stack

## Core Technologies

- **Python 3.11+**: Primary language
- **AWS Bedrock AgentCore**: Serverless agent deployment and scaling
- **LangGraph**: Multi-agent orchestration and state management
- **LangChain**: Tool creation and LLM abstractions
- **DynamoDB**: Operational data storage
- **UV**: Fast Python package and environment manager (replaces pip/virtualenv)

## Key Dependencies

- `bedrock-agentcore>=1.2.0` - AgentCore SDK
- `langchain>=1.2.7` - LangChain framework
- `langgraph>=1.0.7` - Multi-agent orchestration
- `langchain-aws>=1.2.2` - AWS integrations
- `mcp>=1.26.0` - Model Context Protocol
- `python-dotenv>=1.2.1` - Environment management
- `pytest>=9.0.2` - Testing framework
- `hypothesis>=6.151.4` - Property-based testing

## Frontend

- **React 19** with TypeScript
- **Vite** for build tooling
- **Lucide React** for icons

## Build System & Commands

### UV Workflow (Primary)

```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>

# Run commands
uv run python3 script.py
uv run pytest
uv run agentcore dev
uv run agentcore deploy
```

### AgentCore Commands

```bash
# Local development server
uv run agentcore dev

# Deploy to AWS
uv run agentcore deploy

# Invoke agent locally
uv run agentcore invoke --dev "prompt text"

# Invoke deployed agent
uv run agentcore invoke "prompt text"

# View logs
uv run agentcore logs

# Check status
uv run agentcore status
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest test/test_file.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Lint with Ruff
uv run ruff check src/

# Format with Ruff
uv run ruff format src/

# Auto-fix issues
uv run ruff check --fix src/
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # Development server
npm run build    # Production build
npm run preview  # Preview production build
```

## Environment Setup

Required environment variables (see `.env.example`):

- AWS credentials for Bedrock and DynamoDB access
- Region configuration (default: us-east-1)
- MCP Gateway URL (if using external tools)
- Model configuration (Claude Sonnet 4.5 default)
