# L200: AI Agent with Conversational Memory

Build a production-ready AI agent on Databricks with persistent conversation memory, MCP tool integration, and a full-stack chat UI.

## What You'll Build

A conversational agent that:
- **Remembers past conversations** using Lakebase (Databricks-managed PostgreSQL) for session persistence
- **Queries structured data** via Genie Spaces using natural language
- **Searches unstructured documents** via Vector Search for RAG-based retrieval
- **Streams responses** in real-time through a polished chat interface
- **Traces every interaction** with MLflow for observability and debugging

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Next.js Chat UI                        │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              FastAPI Server (MLflow traced)              │
├─────────────────────────────────────────────────────────┤
│           OpenAI Agents SDK (Agent Loop)                 │
├────────────┬────────────────────────────┬───────────────┤
│  Lakebase  │      MCP Servers           │    MLflow     │
│  (Memory)  │  ┌──────────┬───────────┐  │   (Tracing)  │
│            │  │ Vector   │  Genie    │  │              │
│            │  │ Search   │  Space    │  │              │
└────────────┴──┴──────────┴───────────┴──┴───────────────┘
```

## Project Structure

```
medium/
├── agent_server/
│   ├── agent.py              # Agent definition, model, MCP servers
│   ├── start_server.py       # FastAPI server with MLflow setup
│   ├── evaluate_agent.py     # Agent evaluation with MLflow scorers
│   └── utils.py              # Lakebase session, MCP helpers
├── e2e-chatbot-app-next/     # Full-stack chat UI (Next.js + Express)
├── scripts/
│   ├── quickstart.py         # One-command setup
│   └── discover_tools.py     # Find available workspace resources
├── .claude/skills/           # AI assistant skills for common tasks
├── databricks.yml            # Databricks Asset Bundle config
├── app.yaml                  # App runtime configuration
├── pyproject.toml            # Python dependencies
└── SETUP_GUIDE.md            # Detailed setup instructions
```

## Prerequisites

- A Databricks workspace with Unity Catalog enabled
- Databricks CLI installed and authenticated
- Python 3.11+ with `uv` package manager
- Node.js 20+ (for the chat UI)

## Quick Start

```bash
cd medium

# 1. Set up environment (auth, MLflow experiment, dependencies)
uv run quickstart --profile <your-databricks-profile>

# 2. Run locally
uv run start-app

# 3. Deploy to Databricks
databricks bundle deploy --profile <your-profile>
databricks bundle run agent_openai_agents_sdk --profile <your-profile>
```

## Configuration

After running quickstart, customize the agent in `agent_server/agent.py`:

- **NAME** — Your agent's display name
- **SYSTEM_PROMPT** — Instructions that define agent behavior
- **MODEL** — The LLM to use (e.g., `databricks-claude-opus-4-6`)
- **MCP_SERVERS** — Connected tools (Vector Search indexes, Genie Spaces, etc.)

To discover available tools in your workspace:
```bash
uv run discover-tools
```

## Key Features

| Feature | Description |
|---------|-------------|
| Conversation Memory | Lakebase stores session history so the agent recalls prior interactions |
| Vector Search RAG | Search documents and return grounded answers with citations |
| Genie Space Queries | Natural language queries over structured data tables |
| MLflow Tracing | Every agent call is traced for debugging and evaluation |
| Streaming Responses | Real-time token streaming through the chat UI |
| Agent Evaluation | Built-in evaluation script with MLflow scorers |

## Evaluation

Run the built-in evaluation to test agent quality:
```bash
uv run start-app          # Start the agent server
uv run agent-evaluate     # Run evaluation in a separate terminal
```

## Deployment

The app deploys as a Databricks App via Asset Bundles. Update `databricks.yml` with your:
- Workspace host URL
- MLflow experiment ID
- Lakebase project/database details

Then deploy:
```bash
databricks bundle deploy --profile <your-profile>
```

## Learn More

- [Setup Guide](./SETUP_GUIDE.md) — Detailed setup with all configuration options
- [Workspace-Only Setup](./SETUP_GUIDE_WORKSPACE_ONLY.md) — Deploy entirely within Databricks (no local CLI)
- [Agent Framework Docs](https://docs.databricks.com/aws/en/generative-ai/agent-framework/)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
