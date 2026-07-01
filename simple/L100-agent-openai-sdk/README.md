# FreshMart Agent — Getting Started

A production-ready AI agent for FreshMart grocery chain built with the OpenAI Agents SDK. It answers data questions (via Genie) and looks up store policies (via Vector Search).

## Prerequisites

Before starting, ensure you have:

1. **Databricks workspace** with resources created by `01_quickstart_setup.py` (Genie Space, Vector Search index, MLflow experiment)
2. **uv** — Python package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))
3. **Node.js 20+** — for the chat UI ([install via nvm](https://github.com/nvm-sh/nvm))
4. **Databricks CLI** — authenticated to your workspace ([install](https://docs.databricks.com/dev-tools/cli/install.html))

## Quick Start

```bash
# 1. Navigate to this folder
cd simple/L100-agent-openai-sdk

# 2. Run the setup wizard (handles auth, MLflow, .env)
uv run quickstart

# 3. Start the agent + chat UI
uv run start-app
```

Open **http://localhost:3000** to chat with your agent.

## How It Works

```
User (Chat UI on :3000)
  │
  ▼
Agent Server (FastAPI on :8000)
  │
  ├── Genie Space ──► Natural language queries over retail data
  │                   (products, transactions, customers, stores)
  │
  └── Vector Search ──► Policy document lookup
                        (returns, delivery, loyalty, privacy, etc.)
```

The agent uses the **OpenAI Agents SDK** with MCP (Model Context Protocol) servers to connect to Databricks tools. All interactions are traced in **MLflow** for observability.

## Key Files

| File | What it does |
|------|-------------|
| `agent_server/agent.py` | Agent logic — model, system prompt, MCP tools |
| `agent_server/start_server.py` | FastAPI server with MLflow tracing |
| `databricks.yml` | Deployment config (app name, resources, permissions) |
| `.env` | Local environment variables (created by quickstart) |

## Customizing the Agent

### Change the model

Edit `agent_server/agent.py`:
```python
MODEL = 'workshop-ai-endpoint'  # Change to your AI Gateway endpoint
```

### Change the system prompt

Edit the `SYSTEM_PROMPT` variable in `agent_server/agent.py`.

### Add a new tool

Use the `/add-tools` skill in Claude Code, or manually:
1. Add an MCP server entry in `agent_server/agent.py` → `MCP_SERVERS` list
2. Grant permissions in `databricks.yml` → `resources` section
3. Redeploy

## Deploying to Databricks

```bash
# 1. Verify everything works locally
uv run preflight

# 2. Deploy (uploads code, creates/updates app)
databricks bundle deploy

# 3. Start the app (required after deploy!)
databricks bundle run agent_openai_agents_sdk
```

Your app will be available at the URL shown in the deploy output.

## Evaluating the Agent

Use the **`02_agent_evaluation.ipynb`** notebook in the parent directory (`simple/`). It evaluates your deployed agent with MLflow scorers:

- **Completeness** — Does the agent fully answer the question?
- **RelevanceToQuery** — Is the response relevant?
- **Safety** — Does the response follow safety guidelines?
- **ToolCallEfficiency** — Are tools used effectively?

Run it in your Databricks workspace after deploying the agent.

## Using Claude Code

If you have Claude Code installed, these skills guide you through common tasks:

| What you want to do | Skill |
|---------------------|-------|
| Set up for the first time | `/quickstart` |
| Run the agent locally | `/run-locally` |
| See what tools are available | `/discover-tools` |
| Add a new tool (Genie, Vector Search, etc.) | `/add-tools` |
| Create a new Databricks resource | `/create-tools` |
| Change the model or system prompt | `/modify-agent` |
| Deploy to Databricks | `/deploy` |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `uv run quickstart` fails on auth | Run `databricks auth login` manually, then retry |
| Port 8000 already in use | `lsof -ti :8000 \| xargs kill -9` |
| Port 3000 already in use | `lsof -ti :3000 \| xargs kill -9` |
| MCP server connection error | Check that Genie Space and Vector Search index exist (run `01_quickstart_setup.py` first) |
| "App already exists" on deploy | Run `uv run quickstart --app-name <existing-app>` to bind, then deploy |
| Permission errors after deploy | Ensure resources are listed in `databricks.yml` with correct permissions |
