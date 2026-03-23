# Databricks AI Agent Workshop: Retail Grocery Assistant with Long-Term Memory

Build an AI-powered conversational agent on Databricks that combines real-time data querying, document retrieval, and persistent user memory — deployed as a full-stack Databricks App.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Databricks App (Deployed)                        │
│                                                                         │
│  ┌──────────────────────┐       ┌──────────────────────────────────┐   │
│  │   React Chat UI       │──────▶│   FastAPI / MLflow AgentServer   │   │
│  │   (Next.js + Vite)    │◀──────│   (Port 8000)                   │   │
│  │   Port 3000           │ SSE   │                                  │   │
│  └──────────────────────┘       └──────────┬───────────────────────┘   │
│                                             │                           │
│                                    ┌────────▼────────┐                  │
│                                    │  LangGraph Agent │                  │
│                                    │  (Stateful)      │                  │
│                                    └────────┬────────┘                  │
│                                             │                           │
│              ┌──────────────────────────────┼──────────────────┐        │
│              │                              │                  │        │
│   ┌──────────▼──────────┐   ┌──────────────▼───┐  ┌──────────▼─────┐  │
│   │  MCP Tool Servers    │   │  Memory Tools     │  │  LLM Endpoint  │  │
│   │                      │   │                   │  │                │  │
│   │  ● Genie Space       │   │  ● get/save/del   │  │  Claude Sonnet │  │
│   │    (Structured SQL)  │   │    user_memory     │  │  4.5           │  │
│   │                      │   │  ● save/search     │  │  (Foundation   │  │
│   │  ● Vector Search     │   │    task_summary    │  │   Model API)   │  │
│   │    (Policy RAG)      │   │  ● save/search     │  │                │  │
│   │                      │   │    conversations   │  └────────────────┘  │
│   │  ● Code Interpreter  │   │                   │                      │
│   │    (system.ai)       │   └─────────┬─────────┘                      │
│   └──────────────────────┘             │                                │
│                                        │                                │
│                              ┌─────────▼─────────┐                      │
│                              │     Lakebase       │                      │
│                              │   (PostgreSQL)     │                      │
│                              │                    │                      │
│                              │  ● Checkpoints     │                      │
│                              │  ● User Memories   │                      │
│                              │  ● Task Summaries  │                      │
│                              │  ● Conversations   │                      │
│                              │  ● Chat History    │                      │
│                              │  ● Embeddings      │                      │
│                              └────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Message
    │
    ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  React UI   │────▶│  MLflow Agent    │────▶│  LangGraph Agent    │
│  (Browser)  │◀────│  Server (FastAPI) │◀────│  (Orchestration)    │
└─────────────┘ SSE └──────────────────┘     └─────────┬───────────┘
                                                       │
                              ┌─────────────────────┬──┴──┬──────────────┐
                              ▼                     ▼     ▼              ▼
                        ┌──────────┐         ┌─────────┐ ┌────────┐ ┌────────┐
                        │  Genie   │         │ Vector  │ │ Memory │ │  LLM   │
                        │  Space   │         │ Search  │ │ Tools  │ │ Claude │
                        │ (SQL)    │         │ (RAG)   │ │        │ │ 4.5    │
                        └──────────┘         └─────────┘ └───┬────┘ └────────┘
                              │                    │         │
                        ┌─────▼────┐         ┌────▼───┐ ┌───▼──────┐
                        │ Retail   │         │ Policy │ │ Lakebase │
                        │ Data     │         │ Docs   │ │ (PG)     │
                        │ Tables   │         │ Index  │ │          │
                        └──────────┘         └────────┘ └──────────┘
```

---

## What You'll Build

A **FreshMart Grocery Shopping Assistant** that can:

| Capability | Powered By | Description |
|---|---|---|
| **Structured data queries** | Genie Space (MCP) | Query customer accounts, products, transactions, stores via natural language to SQL |
| **Policy document lookup** | Vector Search (MCP) | RAG over store policies — returns, memberships, delivery, recalls, privacy |
| **Long-term user memory** | Lakebase + Embeddings | Remembers user preferences, dietary restrictions, and past interactions across sessions |
| **Task & conversation history** | Lakebase + Embeddings | Tracks what the agent helped with and summarizes past conversations |
| **Code execution** | system.ai Code Interpreter | Runs Python for calculations, data analysis, chart generation |
| **Streaming chat UI** | React + Vercel AI SDK | Real-time streaming responses with Databricks OAuth authentication |

---

## Project Structure

```
workshop-qsic/
├── agent_server/                    # Python agent backend
│   ├── agent.py                     # Core agent logic (LangGraph + MCP tools)
│   ├── utils_memory.py              # 7 memory tools (get/save/delete + task/conversation)
│   ├── utils.py                     # Auth, thread management, streaming helpers
│   ├── start_server.py              # MLflow AgentServer bootstrap
│   └── evaluate_agent.py            # Agent evaluation with 9 MLflow scorers
│
├── e2e-chatbot-app-next/            # Full-stack chat UI
│   ├── client/                      # React + Vite frontend
│   ├── server/                      # Express.js backend
│   ├── packages/                    # Shared libs (auth, db, core, ai-sdk)
│   └── scripts/                     # DB migration scripts
│
├── scripts/                         # Setup & utility scripts
│   ├── quickstart.py                # Interactive setup wizard
│   ├── start_app.py                 # Starts both frontend + backend
│   ├── discover_tools.py            # Discovers available Databricks tools
│   └── grant_lakebase_permissions.py
│
├── .claude/skills/                  # Claude Code skills for AI-assisted development
├── databricks.yml                   # Databricks Asset Bundle config
├── app.yaml                         # Databricks App manifest
├── pyproject.toml                   # Python dependencies (uv)
├── .env.example                     # Environment variable template
└── requirements.txt                 # Points to uv for dependency management
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **LLM** | Claude Sonnet 4.5 (via Databricks Foundation Model API) |
| **Agent Framework** | LangGraph (stateful multi-tool orchestration) |
| **Tool Protocol** | MCP (Model Context Protocol) — Genie, Vector Search, Code Interpreter |
| **Memory Store** | Lakebase (managed PostgreSQL) with semantic embeddings |
| **Tracing & Eval** | MLflow 3 (autologging, 9 predefined scorers, conversation simulator) |
| **Frontend** | React + TypeScript + Vite + Vercel AI SDK |
| **Backend API** | FastAPI via MLflow AgentServer (OpenAI Responses API compatible) |
| **Auth** | Databricks OAuth (U2M) + On-Behalf-Of (OBO) user passthrough |
| **Deployment** | Databricks Apps via Asset Bundles |
| **Package Manager** | uv (Python), npm workspaces (Node.js) |

---

## Prerequisites

- **Databricks workspace** with access to:
  - Foundation Model API endpoints
  - Genie Spaces
  - Vector Search
  - Lakebase
  - Databricks Apps
- **Local tools**:
  - [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
  - [nvm](https://github.com/nvm-sh/nvm) + Node.js 20 LTS
  - [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install)
- **Optional**: [Claude Code](https://docs.anthropic.com/en/docs/claude-code) for AI-assisted development

---

## Getting Started

### Option 1: Quick Start (Recommended)

```bash
# Clone the repository
git clone https://github.com/AnanyaDBJ/databricks-ai-workshops.git
cd databricks-ai-workshops

# Run the interactive setup wizard
uv run quickstart
```

The quickstart script will:
1. Verify `uv`, `nvm`, and Databricks CLI installations
2. Configure Databricks OAuth authentication
3. Create and link an MLflow experiment
4. Configure Lakebase for memory storage
5. Generate your `.env` file
6. Start the agent server and chat app

After setup, start the app anytime with:

```bash
uv run start-app
```

The chat UI will be available at **http://localhost:3000** and the API at **http://localhost:8000**.

### Option 2: Using Claude Code

If you have [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed, the repository includes built-in skills in `.claude/skills/` for AI-assisted development:

```bash
# Start Claude Code in the project directory
claude

# Then ask:
# "Run quickstart to configure authentication"
# "Add a Genie space tool to my agent"
# "Set up Lakebase for user memories"
# "Deploy my agent to Databricks Apps"
```

### Option 3: Manual Setup

1. **Install dependencies**

   ```bash
   # Python
   uv sync

   # Node.js (for chat UI)
   nvm use 20
   cd e2e-chatbot-app-next && npm install && cd ..
   ```

2. **Authenticate with Databricks**

   ```bash
   databricks auth login
   ```

   Set your profile in `.env`:
   ```
   DATABRICKS_CONFIG_PROFILE=DEFAULT
   ```

3. **Create an MLflow experiment**

   ```bash
   DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
   databricks experiments create-experiment /Users/$DATABRICKS_USERNAME/agents-on-apps
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your experiment ID, Lakebase instance, Genie space ID, Vector Search index
   ```

5. **Start the application**

   ```bash
   uv run start-app
   ```

---

## Workshop Modules

### Module 1: Understanding the Agent Architecture

Explore how the agent is built:
- **`agent_server/agent.py`** — The core agent with system prompt, MCP tool initialization, and LangGraph orchestration
- **`agent_server/utils_memory.py`** — Seven memory tools for persistent user preferences and conversation history
- **`agent_server/utils.py`** — Authentication helpers, thread management, streaming utilities

### Module 2: Working with MCP Tools

The agent connects to three MCP (Model Context Protocol) servers:

| MCP Server | Purpose | Endpoint |
|---|---|---|
| `system-ai` | Code Interpreter (Python execution) | `/api/2.0/mcp/functions/system/ai` |
| `retail-grocery-genie` | Natural language to SQL queries | `/api/2.0/mcp/genie/{GENIE_SPACE_ID}` |
| `retail-policy-docs` | RAG over policy documents | `/api/2.0/mcp/vector-search/{INDEX}` |

### Module 3: Long-Term Memory with Lakebase

The memory system uses Lakebase (PostgreSQL) with semantic embeddings:

| Tool | Function | Use Case |
|---|---|---|
| `get_user_memory` | Semantic search on user memories | "What are my dietary preferences?" |
| `save_user_memory` | Persist user info | User says "I'm vegetarian" |
| `delete_user_memory` | Remove specific memories | "Forget my address" |
| `save_task_summary` | Record completed tasks (silent) | After answering a product question |
| `search_task_history` | Query past tasks | "What did you help me with last time?" |
| `save_conversation_summary` | Record conversation end-state (silent) | When user says goodbye |
| `search_past_conversations` | Find previous interactions | "What have we talked about?" |

### Module 4: Evaluating the Agent

Run the evaluation suite with 9 MLflow scorers:

```bash
uv run agent-evaluate
```

**Scorers**: Completeness, ConversationalSafety, ConversationCompleteness, Fluency, KnowledgeRetention, RelevanceToQuery, Safety, ToolCallCorrectness, UserFrustration

### Module 5: Deploying to Databricks Apps

```bash
# Create the app
databricks apps create retail-grocery-ltm-memory

# Sync code to workspace
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks sync . "/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory"

# Deploy
databricks apps deploy retail-grocery-ltm-memory \
  --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory
```

See [Deploying to Databricks Apps](#deploying-to-databricks-apps-1) for full instructions including Lakebase permissions.

---

## API Reference

The agent implements the [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses) interface via MLflow's ResponsesAgent.

### Streaming Request

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "What organic produce do you have?"}], "stream": true}'
```

### Non-Streaming Request

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "What are your return policies?"}]}'
```

### Request with User Context (enables memory)

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{"role": "user", "content": "Remember that I prefer organic produce"}],
    "context": {"user_id": "workshop-user@example.com"}
  }'
```

---

## Modifying Your Agent

### Change the LLM

Edit `LLM_ENDPOINT_NAME` in `agent_server/agent.py`:

```python
LLM_ENDPOINT_NAME = "databricks-claude-sonnet-4-5"  # or any Foundation Model API endpoint
```

### Add New MCP Tools

Add entries to the `init_mcp_client()` function in `agent_server/agent.py`:

```python
DatabricksMCPServer(
    name="my-new-tool",
    url=f"{host_name}/api/2.0/mcp/...",
    workspace_client=workspace_client,
)
```

### Customize the System Prompt

Edit the `SYSTEM_PROMPT` variable in `agent_server/agent.py` to change the agent's personality, capabilities, and guidelines.

### Add Python Dependencies

```bash
uv add <package_name>
```

---

## Deploying to Databricks Apps

1. **Create the app**:
   ```bash
   databricks apps create retail-grocery-ltm-memory
   ```

2. **Add resources** via the Databricks UI (App > Edit > App Resources):
   - MLflow Experiment (CAN_MANAGE)
   - Genie Space (CAN_RUN)
   - Lakebase Instance (CAN_CONNECT_AND_CREATE)
   - Vector Search Index (SELECT)

3. **Grant Lakebase permissions** to the app's service principal:
   ```bash
   uv run python scripts/grant_lakebase_permissions.py
   ```

4. **Sync and deploy**:
   ```bash
   DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
   databricks sync . "/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory"
   databricks apps deploy retail-grocery-ltm-memory \
     --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory
   ```

5. **Query the deployed agent** (requires OAuth token):
   ```bash
   databricks auth token  # copy the token
   curl -X POST <app-url>.databricksapps.com/invocations \
     -H "Authorization: Bearer <oauth-token>" \
     -H "Content-Type: application/json" \
     -d '{"input": [{"role": "user", "content": "hi"}], "stream": true}'
   ```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `Lakebase configuration is required` | Set `LAKEBASE_INSTANCE_NAME` in `.env` or run `uv run quickstart` |
| `302 redirect when querying deployed agent` | Use OAuth token, not PAT. Run `databricks auth token` |
| `Permission denied on Lakebase` | Run `uv run python scripts/grant_lakebase_permissions.py` |
| `Streaming 200 OK but error in stream` | Expected — 200 confirms stream setup; check the error content |
| `GENIE_SPACE_ID not set` | Set in `.env` or pass via `uv run quickstart` |
| `nvm: command not found` | Install nvm: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh \| bash` |

---

## FAQ

**Q: Can I use a different LLM?**
Yes. Change `LLM_ENDPOINT_NAME` in `agent_server/agent.py` to any Foundation Model API endpoint (e.g., `databricks-meta-llama-3-3-70b-instruct`).

**Q: Can I add my own tools?**
Yes. Add UC Functions, Genie Spaces, Vector Search Indexes, or custom MCP servers. See the [Agent Framework Tools docs](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-tool).

**Q: How does On-Behalf-Of (OBO) auth work?**
Use `get_user_workspace_client()` from `agent_server.utils` to authenticate as the requesting user instead of the app service principal. See [OBO docs](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth).

**Q: How do I add custom tracing?**
MLflow autologging captures LLM calls automatically. Add custom spans with `@mlflow.trace` or the MLflow tracing API. See [MLflow tracing docs](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/).

---

## Resources

- [Databricks Agent Framework](https://docs.databricks.com/aws/en/generative-ai/agent-framework/)
- [MLflow ResponsesAgent](https://mlflow.org/docs/latest/genai/flavors/responses-agent-intro/)
- [Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/)
- [Lakebase Documentation](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase)
- [MCP on Databricks](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-tool)
- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/quickstart)
