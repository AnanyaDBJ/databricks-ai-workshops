# Build Production Scale Governed AI Agents in Databricks

> A practical guide to building production-ready AI agents — not toy demos. From zero to deployed, with evaluation, governance, and monitoring baked in from day one.

---

## Getting Started

### 1. Set up your data (required for all levels)

**→ [`data/README.md`](./data/README.md)**

This creates the shared dataset (tables, Vector Search index, Genie Space) that all workshop levels depend on. Takes ~15 minutes.

### 2. Pick your level

Each guide is self-contained — pick one and follow it start to finish.

| Level | What You'll Build | Duration | Guide |
|-------|-------------------|----------|-------|
| **Simple (L100)** | AI agent using managed Databricks services — Genie, Vector Search, Playground. No custom code. | ~2-3 hours | [Lab Guide](./simple/LAB_GUIDE.md) |
| **Medium (L200)** | Custom agent with OpenAI Agents SDK, MCP tools, Lakebase memory, and chat UI deployed as a Databricks App. | ~3-4 hours | [Local Guide](./medium/WORKSHOP_INSTRUCTIONS.md) / [Workspace Guide](./medium/WORKSHOP_INSTRUCTIONS_WORKSPACE.md) |
| **Advanced (L300)** | Production-grade LangGraph agent with MCP, persistent memory, streaming UI, and evaluation suite. | ~5-6 hours | [Local Guide](./advanced/WORKSHOP_INSTRUCTIONS.md) / [Workspace Guide](./advanced/WORKSHOP_INSTRUCTIONS_WORKSPACE.md) |

---

## What You'll Learn

Every level follows the same agent lifecycle:

1. **Build** — Connect LLMs to your data using tools (Genie, Vector Search, UC Functions, MCP)
2. **Evaluate** — MLflow tracing, automated LLM judges, prompt iteration
3. **Govern** — AI Gateway, Unity Catalog permissions, guardrails
4. **Deploy** — Databricks Apps with service principals and observability
5. **Improve** — Human-in-the-loop feedback, labelling sessions, continuous iteration

---

## Repository Structure

```
data/            Shared data setup (run this first)
simple/          L100 — Managed services, no custom code
medium/          L200 — Custom agent with memory (OpenAI Agents SDK + Lakebase)
advanced/        L300 — Full custom stack (LangGraph + MCP + React UI)
```

---

## Why This Exists

There are plenty of "hello world" agent demos. What's missing is the hard part — evaluation, governance, monitoring, and the operational rigor that separates a prototype from a product.

These workshops teach you to build agents that are **tested, governed, observable, and continuously improving.**
