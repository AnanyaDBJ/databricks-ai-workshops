# L200: Build an AI Agent with Memory on Databricks

Go from zero to a production-deployed AI agent that remembers conversations, queries your data, searches your documents, and runs as a full-stack application — all on Databricks.

![L200 Architecture](./L200_Architecture.png)

---

## What You'll Build

By the end of this workshop, you'll have deployed a fully functional AI agent application that:

- **Answers questions about your data** — natural language queries translated to SQL in real time via Genie Spaces
- **Searches documents intelligently** — semantic retrieval over chunked documents using Vector Search (not just keyword matching)
- **Remembers conversations** — persistent memory powered by Lakebase (managed PostgreSQL), so the agent recalls what you discussed yesterday
- **Streams responses** through a polished chat interface with conversation history
- **Traces every interaction** in MLflow — full observability into what the agent did, which tools it called, and how long each step took

This isn't a toy demo. You'll walk away with a deployable application pattern you can adapt for your own use cases.

---

## Architecture Walkthrough

The architecture diagram above shows the complete system you'll build, broken into logical phases:

### Phase 1: Data & Tools (Core Building Blocks)

You start by creating the data resources your agent will use as tools:

- **Vector Search Index** — enables document search by meaning (semantic similarity)
- **Genie Space** — a natural language interface over your structured data tables
- **Unity Catalog Functions** — deterministic computations the agent can call
- **UC Tables** — the underlying business data (customers, transactions, products, etc.)

All of these connect to the agent via **MCP (Model Context Protocol)** — an open standard for tool interoperability.

### Phase 2: Agent Construction

The agent itself is built with:

- **OpenAI Agents SDK** — the agent loop (reasoning, tool selection, response generation)
- **AI Gateway** — Databricks' proxy layer for LLM calls, providing rate limiting, governance, and cost tracking
- **Foundation Models API** — access to Claude, GPT, and open-source models with a single API

### Phase 3: Memory & Persistence

What makes this agent production-grade is **memory**:

- **Lakebase** (managed PostgreSQL) stores two types of data:
  - *Agent memory* — conversation context that persists across sessions, so the agent remembers prior interactions
  - *Chat UI history* — message storage for the frontend sidebar (past conversations you can revisit)

### Phase 4: Full-Stack Deployment

The final application runs as a **Databricks App** with two components:

- **Backend** (Python, port 8000) — FastAPI server running the agent with MLflow tracing
- **Frontend** (Node.js, port 3000) — A Next.js chat interface with streaming responses, conversation history, and message voting

Deployment uses Databricks Asset Bundles — one `databricks bundle deploy` command packages everything.

### Phase 5: Evaluation & Iteration

Once deployed, you'll use:

- **MLflow Tracing** — automatic instrumentation of every agent call for debugging
- **MLflow Evaluation** — score agent quality with built-in and custom metrics
- **Iterative improvement** — use evaluation results to refine prompts, tools, and guardrails

---

## Tech Stack

| Technology | Role in This Workshop |
|---|---|
| OpenAI Agents SDK | Agent reasoning loop and tool orchestration |
| Databricks AI Gateway | LLM governance, rate limiting, cost tracking |
| Vector Search | Semantic document retrieval (RAG) |
| Genie Spaces | Natural language → SQL for structured data |
| Lakebase (PostgreSQL) | Conversation memory and chat history persistence |
| MLflow | Tracing, evaluation, experiment tracking |
| MCP (Model Context Protocol) | Standard interface connecting agent to tools |
| Databricks Apps | Production hosting (compute, networking, auth) |
| Next.js + FastAPI | Frontend chat UI + backend API server |
| Databricks Asset Bundles | Infrastructure-as-code deployment |

---

## Get Started

Choose the setup path that fits your environment:

### Option A: Local Development with Databricks CLI

Best for: developers who want to edit code locally, test on their machine, then deploy.

**Requirements:** Databricks CLI, Python + `uv`, Node.js 20+

> **[Start here: SETUP_GUIDE.md](./lab_instructions/SETUP_GUIDE.md)**

### Option B: Entirely Within Databricks Workspace

Best for: workshops where participants only need a browser — no local installations required.

**Requirements:** A Databricks workspace with Apps, Lakebase, and Web Terminal enabled

> **[Start here: SETUP_GUIDE_WORKSPACE_ONLY.md](./lab_instructions/SETUP_GUIDE_WORKSPACE_ONLY.md)**

Both guides include the data preparation step (creating tables, Vector Search index, and Genie Space from the shared `data/` folder).

---

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
│   ├── quickstart.py         # One-command environment setup
│   ├── discover_tools.py     # Discover available workspace resources
│   └── lakebase_setup_script.ipynb  # Helper for Lakebase configuration
├── databricks.yml            # Deployment configuration (Asset Bundle)
├── lab_instructions/
│   ├── SETUP_GUIDE.md            # Local CLI setup instructions
│   ├── SETUP_GUIDE_WORKSPACE_ONLY.md   # Workspace-only setup instructions
│   ├── L200_Lab_Guide_Local_CLI.html   # Visual lab guide (Local CLI)
│   └── L200_Lab_Guide_Workspace.html   # Visual lab guide (Workspace-only)
```

---

## What You'll Learn

After completing this workshop, you'll be able to:

1. **Build agents with the OpenAI Agents SDK** on Databricks — understanding the agent loop, tool selection, and streaming
2. **Connect real data sources via MCP** — Vector Search for documents, Genie Spaces for SQL, UC functions for computations
3. **Add persistent conversation memory** — using Lakebase so agents maintain context across sessions
4. **Deploy production applications** — full-stack apps on Databricks with proper auth, resource bindings, and service principals
5. **Monitor and evaluate agent quality** — MLflow tracing for debugging, evaluation scorers for quality measurement
6. **Understand the AI Gateway** — governance, rate limiting, and cost control for LLM calls in production

---

## Quick Reference

| Task | Command |
|------|---------|
| Set up environment | `uv run quickstart --profile <profile>` |
| Discover tools in workspace | `uv run discover-tools` |
| Run locally | `uv run start-app` |
| Deploy to Databricks | `databricks bundle deploy && databricks bundle run agent_openai_agents_sdk` |
| Evaluate agent quality | `uv run agent-evaluate` |
| View deployed app logs | `databricks apps logs <app-name> --follow` |
