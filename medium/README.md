# Build an AI Agent with Memory on Databricks (L200)

An AI-powered conversational agent using the OpenAI Agents SDK with Genie, Vector Search, and Lakebase memory — deployed as a full-stack Databricks App.

![L200 Architecture](./L200_Architecture.png)

## Get Started

| Path | Guide |
|------|-------|
| **Local development** (uv, Node.js, CLI on your machine) | [WORKSHOP_INSTRUCTIONS.md](./WORKSHOP_INSTRUCTIONS.md) |
| **Workspace only** (everything in Databricks, no local setup) | [WORKSHOP_INSTRUCTIONS_WORKSPACE.md](./WORKSHOP_INSTRUCTIONS_WORKSPACE.md) |

## Quick Commands

| Command | Description |
|---------|-------------|
| `uv run setup` | Guided end-to-end setup (runs the phases below in order) |
| `uv run quickstart` | Auth, MLflow experiment, Lakebase, `.env` + `databricks.yml` |
| `uv run configure-agent` | Pick tools interactively; writes `agent.py` tool wiring |
| `uv run grant-all` | Grant Lakebase + Unity Catalog + Genie permissions to the app SP |
| `uv run start-app` | Start agent server + chat UI |
| `uv run start-server` | Start agent server only |
| `uv run agent-evaluate` | Run evaluation suite |
| `uv run discover-tools` | Discover available Databricks tools |

Setup is script-driven and input-driven — you supply your resources one prompt at a time. If a script fails in your environment, **[`MANUAL_SETUP.md`](./MANUAL_SETUP.md)** reproduces every step by hand.

## Project Structure

```
medium/
├── agent_server/
│   ├── agent.py              # Agent definition — model, tools, system prompt
│   ├── start_server.py       # FastAPI server + MLflow tracing setup
│   ├── evaluate_agent.py     # Evaluation script with MLflow scorers
│   └── utils.py              # Lakebase memory, MCP helpers
├── e2e-chatbot-app-next/     # Full-stack chat UI (Next.js + Express)
├── scripts/
│   ├── setup.py              # Guided end-to-end setup wrapper
│   ├── quickstart.py         # Auth, experiment, Lakebase, config files
│   ├── configure_agent.py    # Interactive tool-picker; writes agent.py
│   ├── grant_all.py          # Chains Lakebase + UC + Genie permission grants
│   ├── discover_tools.py     # Discover available workspace resources
│   └── lakebase_setup_script.ipynb  # Helper for Lakebase configuration
├── MANUAL_SETUP.md           # By-hand fallback for every setup step
├── databricks.yml            # Deployment configuration (Asset Bundle)
├── app.yaml                  # Databricks App manifest
└── .env.example              # Environment variable template
```
