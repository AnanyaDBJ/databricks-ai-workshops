# Workshop: Build an AI Agent with Memory on Databricks

Build and deploy a conversational AI agent with Genie, Vector Search, and persistent memory using the OpenAI Agents SDK.

## Prerequisites

| Tool | Install |
|------|---------|
| Databricks CLI v0.295+ | `brew tap databricks/tap && brew install databricks` |
| uv | [install guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Node.js 20+ | [nodejs.org](https://nodejs.org) |

Your workspace needs: Unity Catalog, Databricks Apps, Lakebase, Vector Search, and Foundation Model API.

### Data setup (required first)

Complete the data setup before continuing:
**→ [`data/README.md`](../data/README.md) — Path A (Local CLI)**

When done, you should have these values saved:
- **Catalog.Schema** (e.g., `my_catalog.my_schema`)
- **Vector Search Index** (e.g., `my_catalog.my_schema.policy_docs_index`)
- **Genie Space ID** (e.g., `01abcdef12345678`)
- **MLflow Experiment ID** (e.g., `1234567890123456`)

---

## Step 1: Clone the Repo

```bash
git clone https://github.com/AnanyaDBJ/databricks-ai-workshops.git
cd databricks-ai-workshops/medium
```

---

## Step 2: Run Quickstart

```bash
uv run quickstart --profile DEFAULT
```

This interactive wizard handles:
- Databricks CLI authentication (OAuth login)
- MLflow experiment creation
- `.env` file configuration

Follow the prompts. If you already created an experiment in the data setup, pass it:

```bash
uv run quickstart --profile DEFAULT --experiment-id <ID>
```

---

## Step 3: Create a Lakebase Instance

In the Databricks UI, create an **autoscaling** Lakebase project:

1. Go to **Compute** > **Lakebase**
2. Click **Create Project** > choose **Autoscaling**
3. Name it (e.g., `my-agent-workshop`) and click Create
4. Wait for it to show as "Ready"

Find your connection details using the helper notebook:

1. Open `medium/scripts/lakebase_setup_script.ipynb` in your workspace
2. In Cell 3, replace `<project name>` with your project name
3. Run Cell 3 — note the **branch path** and **database path** from the output

> **Important:** Only run Cell 1 (optional) and Cell 3. Do NOT run Cells 2, 4, or 5 — the app creates its own tables automatically.

---

## Step 4: Configure the Agent

### 4a. Update `.env` with Lakebase values

Add these to your `.env` file:

```env
LAKEBASE_AUTOSCALING_ENDPOINT=projects/<your-project>/branches/<your-branch>/endpoints/<your-endpoint>
LAKEBASE_AGENT_MEMORY_SCHEMA=agent_openai_memory
PGHOST=<your-lakebase-hostname>
PGDATABASE=databricks_postgres
PGPORT=5432
PGUSER=<your-email@company.com>
```

### 4b. Edit `agent_server/agent.py` with your tool URLs

Find the `MCP_SERVERS` section and update with your values from the data setup:

```python
MCP_SERVERS = [
    ('Policy Document Search', '/api/2.0/mcp/vector-search/<catalog>/<schema>/<index-name>'),
    ('Data Query Assistant', '/api/2.0/mcp/genie/<genie-space-id>'),
]
```

> **Note:** If your index name is `my_catalog.my_schema.policy_docs_index` (with dots), change dots to slashes in the URL: `my_catalog/my_schema/policy_docs_index`

To discover additional tools: `uv run discover-tools`

---

## Step 5: Run Locally

```bash
uv run start-app
```

This starts the backend (port 8000) and frontend (port 3000). On first run, it automatically creates all database tables.

Open `http://localhost:3000` and try:
- "What is the return policy for perishable items?" (Vector Search)
- "What are the top 5 products by revenue?" (Genie)
- "Remember my name is Alice" then refresh and ask "What's my name?" (Memory)

---

## Step 6: Deploy to Databricks Apps

### 6a. Update `databricks.yml`

Edit the `resources` section with your actual values:

```yaml
resources:
  apps:
    agent_openai_agents_sdk:
      name: "agent-<your-app-name>"
      # ...
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
    workspace:
      host: https://<your-workspace>.cloud.databricks.com
```

### 6b. Validate and Deploy

```bash
# Validate configuration
databricks bundle validate --profile DEFAULT

# Deploy (uploads code, creates app + resources)
databricks bundle deploy --profile DEFAULT

# Start the app
databricks bundle run agent_openai_agents_sdk --profile DEFAULT
```

> `bundle deploy` uploads files and creates resources. `bundle run` starts the app.

---

## Step 7: Grant Permissions

After the first deploy, the app's service principal needs access to tables you created during local testing.

Get the SP identity:

```bash
databricks apps get <your-app-name> --output json --profile DEFAULT | jq -r '.service_principal_client_id'
```

Connect to your Lakebase instance (via psql, notebook, or any PostgreSQL client) and run:

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

-- Drizzle migration tracking
GRANT USAGE ON SCHEMA drizzle TO PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA drizzle TO PUBLIC;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA drizzle TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle GRANT ALL ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO PUBLIC;
```

> **Alternative:** If you prefer no grants, drop all schemas before deploying and let the app's SP create them fresh.

---

## Step 8: Verify the Deployed App

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
  -d '{"input": [{"role": "user", "content": "Hello, what tools do you have?"}]}'
```

Open the app URL in your browser to use the chat UI.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `relation "ai_chatbot"."Chat" already exists` | Drop schemas: `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` then restart |
| `relation agent_messages does not exist` | Restart the app — `start_server.py` auto-creates them |
| `permission denied for schema` | Run the GRANT statements in Step 7 |
| `permission denied for sequence` | Sequences need separate grants — run full Step 7 SQL |
| App crashes after deploy | Check `databricks apps logs` — usually a missing env var or permission issue |
| `databricks bundle deploy` says "unknown field" | Upgrade CLI to v0.295.0+ |
| `An app with the same name already exists` | Delete: `databricks apps delete <name>` or bind: `databricks bundle deployment bind agent_openai_agents_sdk <name> --auto-approve` |
| MCP tools not responding | Verify URLs in `agent.py` match resources from data setup. Format: `/api/2.0/mcp/vector-search/catalog/schema/index` |
| Vector Search returns no results | Index may not be synced — wait 5-10 min after creation |
| Local app won't start | Check `lsof -ti :8000` — kill orphan processes |
