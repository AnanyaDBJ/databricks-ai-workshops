# Build an AI Agent with Memory on Databricks (L200)

Build a **chatbot that answers questions about your data** — it searches documents, queries
your tables in plain English (Genie), and remembers the conversation — then deploy it as a
live web app on Databricks. You run it locally first, then ship it.

![L200 Architecture](./L200_Architecture.png)

## Get started

New here? Open a guide and follow it end to end — it's seven steps, and each explains what
you're doing and why. Pick the path that matches where you want to work:

| Path | Guide |
|------|-------|
| **On your laptop** (you have a terminal, uv, Node.js) | [WORKSHOP_INSTRUCTIONS.md](./WORKSHOP_INSTRUCTIONS.md) |
| **Entirely in Databricks** (nothing installed locally) | [WORKSHOP_INSTRUCTIONS_WORKSPACE.md](./WORKSHOP_INSTRUCTIONS_WORKSPACE.md) |

Either way, do the shared **[data setup](../data/README.md)** first — it creates the tables,
documents, and search index the agent uses.

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

> **No `uv`?** `uv` is only the local runner (deployment uses it on the app's own compute regardless). Run `pip install -e .` once with Python 3.12, then use the bare command names (`quickstart`, `configure-agent`, …) instead of `uv run …`. See [`MANUAL_SETUP.md` → Running without uv](./MANUAL_SETUP.md#running-without-uv).

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
