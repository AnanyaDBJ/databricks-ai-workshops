# Governed AI Agents on Databricks

A hands-on workshop series for building governed, production-ready AI agents on the Databricks platform. Each level progressively introduces more complexity — from managed services to fully custom agentic architectures.

## Workshop Levels

| Level | Focus | What You'll Build |
|-------|-------|-------------------|
| **Simple** | Managed capabilities | Agents using Databricks managed services, deployed at enterprise scale with built-in governance |
| **Medium** | Managed + Custom | Agentic systems that combine managed services with custom components on the Databricks platform |
| **[Advanced](./advanced/)** | Full custom stack | A production-grade AI solution using LangGraph, MCP tools, and Lakebase for persistent memory |

## End-to-End Agent Lifecycle

Across all three levels, the workshops follow the same lifecycle — the implementation just gets deeper at each stage:

1. **Using LLMs for Enterprise AI** — model selection, prompt engineering, and endpoint configuration
2. **Building Agents** — tool integration, memory, orchestration patterns
3. **Evaluation & Iteration** — systematic quality assessment with MLflow scorers
4. **Human-in-the-Loop** — self-improving agents through feedback loops
5. **Governance & Monitoring** — access control, tracing, and production observability
6. **AgentOps** — end-to-end operationalization from dev to deployment

## Getting Started

Each level is self-contained with its own implementation and instructions. Pick the level that matches your experience and dive in:

```
simple/        # Start here if you're new to Databricks AI
medium/        # Familiar with the basics, ready to customize
advanced/      # Ready to build production-grade agentic systems
```

> All workshops are compatible with coding agents (Claude Code, Cursor, etc.) — skills and context files are included. That said, the goal is to learn the concepts first, then build. Understanding *why* matters more than copy-pasting *what*.

## What You'll Walk Away With

By the end of any workshop level, you'll have a working understanding of how agents are built, evaluated, governed, and deployed on Databricks. The patterns here are designed to be future-proof — rooted in fundamentals that transfer across tools and frameworks.

The difference between a basic agent and a great one is in how you design it. Start building.
