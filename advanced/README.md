# Retail Grocery AI Agent with Long-Term Memory (L300)

An AI-powered conversational agent on Databricks that combines real-time data querying, document retrieval, and persistent user memory — deployed as a full-stack Databricks App.

![L300 Architecture](./L300_Architecture.png)

## Get Started

| Path | Guide |
|------|-------|
| **Local development** (uv, Node.js, CLI on your machine) | [WORKSHOP_INSTRUCTIONS.md](./WORKSHOP_INSTRUCTIONS.md) |
| **Workspace only** (everything in Databricks, no local setup) | [WORKSHOP_INSTRUCTIONS_WORKSPACE.md](./WORKSHOP_INSTRUCTIONS_WORKSPACE.md) |

## Quick Commands

| Command | Description |
|---------|-------------|
| `uv run quickstart` | Interactive setup wizard |
| `uv run start-app` | Start agent server + chat UI |
| `uv run start-server` | Start agent server only |
| `uv run agent-evaluate` | Run evaluation suite |
| `uv run discover-tools` | Discover available Databricks tools |

## Project Structure

```
advanced/
├── agent_server/
│   ├── agent.py            # Core agent: LLM, tools, invoke/stream
│   ├── utils_memory.py     # Memory tools (user prefs, tasks, conversations)
│   └── utils.py            # Auth, threading, streaming helpers
├── scripts/
│   ├── quickstart.py       # Setup wizard
│   └── start_app.py        # Starts frontend + backend
├── databricks.yml          # Asset Bundle config (deployment)
├── app.yaml                # Databricks App manifest
└── .env.example            # Environment variable template
```
