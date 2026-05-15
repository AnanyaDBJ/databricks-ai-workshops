# L100: Build Your First AI Agent on Databricks

Create a conversational AI assistant for a fictional grocery chain called **FreshMart** — using only managed Databricks services, no coding required after setup.

---

## What You'll Build

| Capability | Powered By |
|---|---|
| Natural language data queries | Genie Space |
| Semantic document search (RAG) | Vector Search |
| LLM governance & guardrails | AI Gateway |
| Conversational agent (no code) | Playground + Managed Agents |
| Production deployment with chat UI | Databricks Apps |
| Automated quality evaluation | MLflow Tracing + LLM Judges |
| Human feedback & labelling | Review App |

---

## Get Started

**Full step-by-step instructions:** [`LAB_GUIDE.md`](./LAB_GUIDE.md)

The lab guide covers 8 sections (~3 hours self-paced, ~2.5 hours instructor-led):

1. Data & resource setup
2. AI Gateway
3. Genie, Vector Search, Playground
4. Deploy agent app
5. MLflow evaluation
6. Human-in-the-loop
7. Managed agents (Knowledge Assistant + Supervisor)
8. Document Intelligence (coming soon)

---

## Prerequisites

- Databricks workspace with serverless SQL compute
- Foundation Model API access (Claude Sonnet 4 or Llama 3.3 70B)
- Unity Catalog with permission to create schemas
- Vector Search and Databricks Apps enabled

No local tools required — everything runs in the browser.

---

## Folder Contents

| Path | Purpose |
|------|---------|
| `LAB_GUIDE.md` | Complete workshop instructions (start here) |
| `L100-agent-openai-sdk/` | Agent app source code (OpenAI Agents SDK + MCP) |
| `01_simple_agent_evaluation.ipynb` | Evaluation notebook with MLflow judges |
