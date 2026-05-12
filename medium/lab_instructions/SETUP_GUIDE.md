# Setup Guide: Deploy This Agent with CLI + Local Development

This guide walks you through setting up the workshop data, cloning this codebase, testing locally, and deploying as a Databricks App with Lakebase-powered short-term memory and chat history.

---

## Prerequisites

- A Databricks workspace with Unity Catalog enabled
- Databricks CLI v0.295.0+ installed (`brew install databricks` or `pip install databricks-cli`)
- `uv` (Python package manager) installed
- Node.js 20+ with npm (for the frontend)
- Access to create Lakebase instances in the workspace

---

## Step 1: Clone the Repository

```bash
git clone <repo-url>
cd <repo-name>
```

---

## Step 2: Prepare Workshop Data

Before setting up the agent app, you need to create the data resources (tables, Vector Search index, Genie Space) that the agent will use as tools.

**Option A — Run the setup notebook in Databricks (recommended):**

1. Import the repo into your workspace (Repos → Add → Git Folder)
2. Open `data/workspace_setup_script/01_quickstart_setup.py`
3. Fill in catalog and schema widgets → **Run All**
4. Note the outputs:
   - **MLflow Experiment ID**
   - **Vector Search Index name** (e.g., `catalog.schema.policy_docs_index`)
   - **Genie Space ID**

**Option B — Run local scripts (if you prefer CLI):**

The `data/local_cli_setup_script/` folder has Python scripts that create the same resources via REST API:

```bash
cd data/local_cli_setup_script

# Generate structured data tables
python execute_sql.py --profile DEFAULT --warehouse-id <WAREHOUSE_ID>

# Chunk policy documents
python execute_chunking.py --profile DEFAULT --warehouse-id <WAREHOUSE_ID>
```

> **Note:** With Option B, you still need to manually create the Vector Search endpoint+index, Genie Space, and MLflow experiment. See the `data/README.md` for details.

---

## Step 3: Authenticate with Databricks CLI

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

This creates a profile (default: `DEFAULT`). Verify with:

```bash
databricks auth profiles
```

---

## Step 4: Run Quickstart

```bash
cd medium
uv run quickstart --profile DEFAULT
```

This will:
- Create a `.env` file with your profile
- Create (or reuse) an MLflow experiment
- Update `databricks.yml` with the experiment ID

> If you already created an experiment in Step 2, pass it: `uv run quickstart --profile DEFAULT --experiment-id <ID>`

---

## Step 5: Create a Lakebase Instance

In the Databricks UI or via CLI, create an **autoscaling** Lakebase project and branch. Note down:

- The **endpoint path**: `projects/<project-name>/branches/<branch-name>/endpoints/<endpoint-name>`
- The **branch path**: `projects/<project-name>/branches/<branch-name>`
- The **database path**: `projects/<project-name>/branches/<branch-name>/databases/<db-name>`
- The **PGHOST** hostname (e.g., `ep-xxxx-yyyy.database.<region>.cloud.databricks.com`)

> **Tip:** Run Cell 1 of `medium/scripts/lakebase_setup_script.ipynb` to list branches and endpoints. Run Cell 3 to find the database ID.

---

## Step 6: Update `.env` for Local Development

Edit `.env` to add Lakebase configuration:

```env
DATABRICKS_CONFIG_PROFILE=DEFAULT
MLFLOW_EXPERIMENT_ID=<your-experiment-id>  # set by quickstart
CHAT_APP_PORT=3000
CHAT_PROXY_TIMEOUT_SECONDS=300
MLFLOW_TRACKING_URI="databricks"
MLFLOW_REGISTRY_URI="databricks-uc"

# Lakebase short-term memory (backend agent memory)
LAKEBASE_AUTOSCALING_ENDPOINT=projects/<your-project>/branches/<your-branch>/endpoints/<your-endpoint>
LAKEBASE_AGENT_MEMORY_SCHEMA=agent_openai_memory

# Frontend Lakebase connection (for chat history sidebar)
PGHOST=<your-lakebase-hostname>
PGDATABASE=databricks_postgres
PGPORT=5432
PGUSER=<your-email@company.com>
```

---

## Step 7: Update `databricks.yml` with Your Resources

Edit the `resources` section to point to your Lakebase instance and experiment:

```yaml
resources:
  apps:
    agent_openai_agents_sdk:
      name: "agent-<your-app-name>"   # Choose a unique app name
      description: "OpenAI Agents SDK agent application"
      source_code_path: ./
      config:
        command: ["uv", "run", "start-app"]
        env:
          - name: MLFLOW_TRACKING_URI
            value: "databricks"
          - name: MLFLOW_REGISTRY_URI
            value: "databricks-uc"
          - name: API_PROXY
            value: "http://localhost:8000/invocations"
          - name: CHAT_APP_PORT
            value: "3000"
          - name: CHAT_PROXY_TIMEOUT_SECONDS
            value: "300"
          - name: MLFLOW_EXPERIMENT_ID
            value_from: "experiment"
          - name: LAKEBASE_AUTOSCALING_ENDPOINT
            value_from: "postgres"
          - name: LAKEBASE_AGENT_MEMORY_SCHEMA
            value: "agent_openai_memory"
          - name: PGDATABASE
            value: "databricks_postgres"
          - name: PGPORT
            value: "5432"

      resources:
        - name: 'experiment'
          experiment:
            experiment_id: "<your-experiment-id>"
            permission: 'CAN_MANAGE'
        - name: 'postgres'
          postgres:
            branch: "projects/<your-project>/branches/<your-branch>"
            database: "projects/<your-project>/branches/<your-branch>/databases/<your-db>"
            permission: 'CAN_CONNECT_AND_CREATE'
```

Also update the workspace `host` in `targets`:

```yaml
targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://<your-workspace>.cloud.databricks.com
  prod:
    mode: production
    workspace:
      host: https://<your-workspace>.cloud.databricks.com
    resources:
      apps:
        agent_openai_agents_sdk:
          name: agent-<your-app-name>
```

---

## Step 8: Customize the Agent

Edit `agent_server/agent.py` to configure the model, system prompt, and tools:

```python
NAME = 'my-agent'
SYSTEM_PROMPT = 'You are a helpful assistant specialized in...'
MODEL = 'databricks-claude-sonnet-4-6'  # or your preferred model
MCP_SERVERS = [
    # Use the Vector Search index and Genie Space from Step 2
    ('Policy Document Search', '/api/2.0/mcp/vector-search/<catalog>/<schema>/<index-name>'),
    ('Data Query Assistant', '/api/2.0/mcp/genie/<genie-space-id>'),
]
```

To discover additional tools available in your workspace:

```bash
uv run discover-tools
```

---

## Step 9: Test Locally

```bash
uv run start-app
```

This starts both the backend (port 8000) and frontend (port 3000). On first run, it automatically:
- Creates `agent_openai_memory` schema + tables (backend agent memory)
- Runs Drizzle migrations to create `ai_chatbot` schema + tables (frontend chat history)

Open `http://localhost:3000` (or the port shown in the output). Send messages and verify:
- The agent responds using your MCP tools
- Chat history persists in the sidebar after page refresh
- The agent remembers context within a conversation

> **Note:** If you see migration errors about tables already existing, it means tables were previously created by another method. Drop them:
> ```bash
> # Connect to Lakebase via psql or a notebook and run:
> DROP SCHEMA IF EXISTS ai_chatbot CASCADE;
> DROP SCHEMA IF EXISTS drizzle CASCADE;
> ```
> Then restart `uv run start-app`.

---

## Step 10: Deploy to Databricks Apps

```bash
# Validate configuration
databricks bundle validate --profile DEFAULT

# Deploy (uploads code, creates app + resources)
databricks bundle deploy --profile DEFAULT

# Start the app
databricks bundle run agent_openai_agents_sdk --profile DEFAULT
```

> **Note:** `bundle deploy` only uploads files and creates resources. `bundle run` is required to actually start/restart the app.

---

## Step 11: Grant Permissions to the App's Service Principal

After the first deploy, the app's service principal needs access to the Lakebase schemas that were created during local testing (Step 9). Since YOU created those tables locally, your user owns them — the app's SP needs explicit grants.

> **Why this is needed:** When you tested locally (Step 9), the tables were created under your user identity. The deployed app runs as a service principal, which doesn't own those tables and can't access them without grants.
>
> **Alternative:** If you prefer no grants, you can drop all schemas before deploying and let the app's SP create them fresh (it owns what it creates). See the note in Step 9.

Get the SP identity:

```bash
databricks apps get <your-app-name> --output json --profile DEFAULT | jq -r '.service_principal_client_id'
```

Connect to your Lakebase instance (via `psql`, a Databricks notebook, or any PostgreSQL client) and run:

```sql
-- Backend agent memory schema
GRANT USAGE ON SCHEMA agent_openai_memory TO PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA agent_openai_memory TO PUBLIC;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA agent_openai_memory TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA agent_openai_memory GRANT ALL ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA agent_openai_memory GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO PUBLIC;

-- Frontend chat history schema
GRANT USAGE ON SCHEMA ai_chatbot TO PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA ai_chatbot TO PUBLIC;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA ai_chatbot TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai_chatbot GRANT ALL ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai_chatbot GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO PUBLIC;

-- Drizzle migration journal (so the SP can read which migrations are applied)
GRANT USAGE ON SCHEMA drizzle TO PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA drizzle TO PUBLIC;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA drizzle TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle GRANT ALL ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO PUBLIC;
```

> **Important:** You must grant on SEQUENCES separately. Table grants alone are not enough. Without this, the service principal will get "permission denied for sequence" errors.

---

## Step 12: Verify the Deployed App

```bash
# Check app status
databricks apps get <your-app-name> --output json --profile DEFAULT | jq '{app_status, compute_status, url}'

# View logs
databricks apps logs <your-app-name> --follow --profile DEFAULT

# Test the endpoint
TOKEN=$(databricks auth token --profile DEFAULT | jq -r '.access_token')
APP_URL=$(databricks apps get <your-app-name> --output json --profile DEFAULT | jq -r '.url')

curl -X POST ${APP_URL}/invocations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "Hello, remember my name is Alice"}], "stream": false}'
```

---

## Key Config Values to Replace

| Placeholder | Where to find it |
|---|---|
| `<your-workspace>` | Your Databricks workspace URL |
| `<your-experiment-id>` | Created by quickstart or the data setup notebook (Step 2) |
| `<your-project>` | Lakebase project name (from Lakebase UI) |
| `<your-branch>` | Lakebase branch name (usually `production`) |
| `<your-endpoint>` | Lakebase endpoint name (usually `primary`) |
| `<your-db>` | Lakebase database ID (use Cell 3 of lakebase_setup_script.ipynb) |
| `<your-lakebase-hostname>` | PGHOST value (from Lakebase connection info) |
| `<your-email>` | Your Databricks login email (for PGUSER locally) |
| `<your-app-name>` | Name you choose for the Databricks App |
| `<catalog>/<schema>/<index-name>` | Vector Search index from Step 2 |
| `<genie-space-id>` | Genie Space ID from Step 2 |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `relation "ai_chatbot"."Chat" already exists` | Tables were created by another method. Drop schemas: `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` then restart |
| `relation agent_messages does not exist` | Agent memory tables not created. Restart the app — `start_server.py` auto-creates them. Or run Cell 2 of `lakebase_setup_script.ipynb` |
| `permission denied for schema` | SP can't access user-owned tables. Run the GRANT statements in Step 11 |
| `permission denied for sequence` | Run the GRANT on sequences in Step 11 (sequences need separate grants) |
| App crashes after deploy | Check `databricks apps logs` — usually a missing env var or permission issue |
| Frontend shows no chat history | Verify `PGDATABASE` and `PGPORT` are set in `databricks.yml` and the postgres resource is bound. Check migration ran successfully in logs. |
| `databricks bundle deploy` says "unknown field" | Databricks CLI too old — upgrade to v0.295.0+ |
| `An app with the same name already exists` | Delete: `databricks apps delete <name>` or bind: `databricks bundle deployment bind agent_openai_agents_sdk <name> --auto-approve` |
| MCP tools not responding | Verify URLs in `agent.py` MCP_SERVERS match the resources created in Step 2. Format: `/api/2.0/mcp/vector-search/catalog/schema/index` |
| Vector Search returns no results | Index may not be synced. Wait 5-10 min after creation, or trigger sync manually in Catalog Explorer. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Databricks App                         │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────────┐    │
│  │  Frontend (3000) │─────▶│   Backend (8000)     │    │
│  │  React Chat UI + │      │   FastAPI + MLflow   │    │
│  │  History Sidebar │      │   OpenAI Agents SDK  │    │
│  └────────┬─────────┘      └──────────┬───────────┘    │
│           │                            │                │
└───────────┼────────────────────────────┼────────────────┘
            │                            │
            ▼                            ▼
   ┌─────────────────┐        ┌─────────────────────┐
   │   Lakebase PG   │        │    Lakebase PG      │
   │  Schema:        │        │  Schema:            │
   │  ai_chatbot     │        │  agent_openai_memory│
   │  (UI history)   │        │  (agent memory)     │
   └─────────────────┘        └─────────────────────┘
```

- **Backend memory** (`agent_openai_memory`): Server-side session memory so the agent recalls conversation context across requests
- **Frontend history** (`ai_chatbot`): Persists chat conversations for the sidebar UI (shows past conversations after page refresh)
- Both schemas live in the same Lakebase instance but serve different purposes
