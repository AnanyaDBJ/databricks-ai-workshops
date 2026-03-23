# CLAUDE.md — Agent Development Guide

## Project Overview

This is a **Databricks Agent Framework** project that implements a FreshMart retail grocery conversational agent with long-term memory. It uses LangGraph for orchestration, MCP for tool connectivity, and Lakebase for persistent storage.

## Quick Commands

```bash
uv run quickstart       # Interactive setup wizard
uv run start-app        # Start agent server + chat UI
uv run start-server     # Start agent server only
uv run agent-evaluate   # Run evaluation suite
uv run discover-tools   # Discover available Databricks tools
```

## Key Files

- `agent_server/agent.py` — Core agent: LLM config, system prompt, MCP tools, invoke/stream handlers
- `agent_server/utils_memory.py` — 7 memory tools (user prefs, task summaries, conversation history)
- `agent_server/utils.py` — Auth helpers, thread management, streaming
- `agent_server/evaluate_agent.py` — Evaluation with 9 MLflow scorers
- `scripts/quickstart.py` — Setup wizard
- `scripts/start_app.py` — Starts frontend + backend together
- `databricks.yml` — Databricks Asset Bundle config
- `app.yaml` — Databricks App manifest

## Architecture

- **LLM**: Claude Sonnet 4.5 via `databricks-claude-sonnet-4-5` endpoint
- **Agent**: LangGraph with `StatefulAgentState`
- **Tools**: MCP servers (Genie, Vector Search, system.ai) + custom memory tools
- **Memory**: Lakebase (PostgreSQL) with `databricks-gte-large-en` embeddings (1024 dims)
- **Frontend**: React + Vite + Vercel AI SDK (port 3000)
- **Backend**: FastAPI via MLflow AgentServer (port 8000)
- **API**: OpenAI Responses API interface

## Development Patterns

- Dependencies managed with `uv` (Python) and `npm workspaces` (Node.js)
- Environment config via `.env` file (copy from `.env.example`)
- Authentication: Databricks OAuth via CLI or PAT
- Tracing: MLflow autologging (automatic for LangChain)
- Deployment: Databricks Apps via `databricks sync` + `databricks apps deploy`

## Testing

```bash
# Local testing
uv run start-app
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "hi"}]}'

# With memory (requires user_id)
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "hi"}], "context": {"user_id": "test@example.com"}}'

# Evaluation
uv run agent-evaluate
```
