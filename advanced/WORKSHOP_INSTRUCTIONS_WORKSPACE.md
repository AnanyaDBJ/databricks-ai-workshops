# Workshop: Deploy Retail Grocery AI Agent (Workspace Only)

This guide walks you through deploying the L300 AI agent app **entirely from within a Databricks workspace** — no local machine setup, no terminal installations needed on your laptop.

By the end, you'll have a full-stack chat application with long-term memory, document search, and data querying — deployed as a Databricks App.

---

## Prerequisites

Before you start, confirm your Databricks workspace has these features enabled (ask your workspace admin if unsure):

- **Unity Catalog** — for organizing data tables and permissions
- **Databricks Apps** — for hosting the chat application
- **Lakebase** — managed PostgreSQL database (used for agent memory + chat history)
- **Vector Search** — for semantic document retrieval
- **Foundation Model API** — Claude access via Databricks endpoints
- **Web Terminal** — an in-browser terminal (Settings > Developer > Web Terminal)
- A **running SQL warehouse** — needed to create data tables (Compute > SQL Warehouses)

---

## Step 1: Import the Repository into Your Workspace

This brings the code into your Databricks workspace so you can edit and deploy it.

1. In the left sidebar, click **Workspace** > **Repos** (may also appear as "Git Folders")
2. Click **Add** > **Git Folder**
3. Paste the repository URL: `https://github.com/AnanyaDBJ/databricks-ai-workshops.git`
4. Click **Create Git Folder**

Once imported, your code will be at a path like:
`/Workspace/Repos/<your-username>/databricks-ai-workshops/`

---

## Step 2: Set Up Your Data

Complete **Path B (Workspace Notebook)** from [`data/README.md`](../data/README.md#path-b-workspace-notebook).

When done, save these 4 values from the notebook output — you'll need them in Step 5:

| What to copy | Looks like | You'll use it in |
|------|---------|---------|
| MLflow Experiment ID | `1234567890123456` | Step 5 (`databricks.yml`) |
| Vector Search Index name | `my_catalog.my_schema.policy_docs_index` | Step 5 (`databricks.yml`) |
| Genie Space ID | `01abcdef12345678` | Step 5 (`databricks.yml`) |
| Catalog.Schema | `my_catalog.my_schema` | Step 7 (permissions) |

---

## Step 3: Create a Lakebase Instance

Lakebase is a managed PostgreSQL database inside Databricks. Your app uses it for:
- **Agent long-term memory** (remembers user preferences across sessions)
- **Chat UI history** (persistent conversation sidebar)

### Create the instance

1. In the left sidebar, go to **Compute** > **Lakebase**
2. Click **Create Project** > choose **Autoscaling**
3. Name it something memorable (e.g., `l300-workshop`)
4. Click Create — a `production` branch is created automatically (or name your branch)
5. Wait ~1-2 minutes for it to show as "Ready"

### Find your connection details

You need two paths that tell the app where your database lives:

**Option A — From the Lakebase UI:**
1. Click your project name
2. Click on the branch (e.g., `production`)
3. Note the **Project name** and **Branch name**

**Option B — From a notebook:**
```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
# List databases in your branch
dbs = w.api_client.do("GET", f"/api/2.0/postgres/projects/<project-name>/branches/<branch-name>/databases")
print(dbs)
```

From this, note:
- **Project name**: e.g., `l300-workshop`
- **Branch name**: e.g., `production` or `l300-workshop-branch`
- **Branch path**: `projects/l300-workshop/branches/production`
- **Database path**: `projects/l300-workshop/branches/production/databases/databricks-postgres`

---

## Step 3 (Alternative): Using a Lakebase Provisioned Instance

If your workspace uses a **Provisioned** Lakebase instance (instead of Autoscaling), follow these steps instead:

1. In the left sidebar, go to **Compute** > **Lakebase**
2. Click **Create** > choose **Provisioned**
3. Name it something memorable (e.g., `l300-workshop`)
4. Select a capacity (e.g., `CU_1` for the smallest size)
5. Click Create and wait for it to show as "Running"

The only value you need is the **instance name** — this is simply the name you chose (e.g., `l300-workshop`).

When you get to Step 5, see the "Provisioned Lakebase" note for the different configuration.

---

## Step 4: Confirm the MLflow Experiment ID

The data setup notebook (Step 2) already created an MLflow experiment for you. Confirm the **Experiment ID**:

1. In the left sidebar, click **Experiments**
2. Find the experiment created by the notebook (look for the name printed in Step 2's output)
3. Click on it — the **Experiment ID** is the long number in your browser's URL bar (e.g., the `1234567890123456` part of `.../ml/experiments/1234567890123456`)

**If you can't find it or need a new one:**
1. Go to **Experiments** in the left sidebar
2. Click **Create Experiment** (top-right)
3. Give it a name (e.g., `l300-retail-agent`)
4. Click Create — copy the Experiment ID from the URL

---

## Step 5: Edit `databricks.yml`

Navigate to `advanced/databricks.yml` in the workspace file browser and edit it. This file tells Databricks how to deploy your app and what resources it needs.

### Find-and-replace these values:

| Find this | Replace with | Where you got it |
|---|---|---|
| `"4040511589772447"` (experiment_id) | Your Experiment ID | Step 4 |
| `"01f1595900051132b572b1f717285d6f"` (space_id) | Your Genie Space ID | Step 2 |
| `"ai_days_experiment_catalog.retail_agent.policy_docs_index"` (securable_full_name) | Your `catalog.schema.policy_docs_index` | Step 2 |
| `"l300-workshop-smoke-test"` (LAKEBASE_AUTOSCALING_PROJECT value) | Your Lakebase project name | Step 3 |
| `"l300-workshop-smoke-test-branch"` (LAKEBASE_AUTOSCALING_BRANCH value) | Your Lakebase branch name | Step 3 |
| `"projects/l300-workshop-smoke-test/branches/l300-workshop-smoke-test-branch"` (postgres branch) | Your branch path | Step 3 |
| `"projects/l300-workshop-smoke-test/branches/l300-workshop-smoke-test-branch/databases/databricks-postgres"` (postgres database) | Your database path | Step 3 |

### Here's what the key sections should look like after your edits:

```yaml
bundle:
  name: retail_grocery_ltm_memory

resources:
  apps:
    retail_grocery_ltm_memory:
      name: "retail-grocery-ltm-memory"
      description: "Retail grocery conversational agent with Genie, Vector Search, and long-term memory"
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
          - name: LAKEBASE_AUTOSCALING_PROJECT
            value: "l300-workshop"                    # ← your project name
          - name: LAKEBASE_AUTOSCALING_BRANCH
            value: "production"                       # ← your branch name
          - name: GENIE_SPACE_ID
            value_from: "retail_grocery_genie"
          - name: VECTOR_SEARCH_INDEX
            value_from: "policy_docs_index"
      resources:
        - name: "experiment"
          experiment:
            experiment_id: "1234567890123456"         # ← from Step 4
            permission: "CAN_MANAGE"
        - name: "retail_grocery_genie"
          genie_space:
            name: "Retail Data"
            space_id: "01abcdef12345678"              # ← from Step 2
            permission: "CAN_RUN"
        - name: "postgres"
          postgres:
            branch: "projects/l300-workshop/branches/production"                              # ← from Step 3
            database: "projects/l300-workshop/branches/production/databases/databricks-postgres"  # ← from Step 3
            permission: "CAN_CONNECT_AND_CREATE"
        - name: "policy_docs_index"
          uc_securable:
            securable_full_name: "my_catalog.my_schema.policy_docs_index"   # ← from Step 2
            securable_type: "TABLE"
            permission: "SELECT"

targets:
  dev:
    mode: development
    default: true
    workspace:
      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/retail_grocery_ltm_memory/${bundle.target}
```

### Provisioned Lakebase — different configuration

If you're using a Provisioned instance (Step 3 Alternative), make these changes instead:

1. Replace the `postgres` resource with a `database` resource:
```yaml
        - name: "postgres"
          database:
            database_name: databricks_postgres
            instance_name: "l300-workshop"            # ← your instance name
            permission: CAN_CONNECT_AND_CREATE
```

2. Replace the Lakebase env vars:
```yaml
          - name: LAKEBASE_INSTANCE_NAME
            value: "l300-workshop"                    # ← your instance name
```
(Remove `LAKEBASE_AUTOSCALING_PROJECT` and `LAKEBASE_AUTOSCALING_BRANCH`)

---

## Step 6: Deploy the App

Open the **Web Terminal**: click the `>_` terminal icon in the bottom panel of your workspace, or go to Settings > Developer > Web Terminal.

### Deploy steps

1. Navigate to the `advanced` folder:
   ```bash
   cd /Workspace/Repos/<your-username>/databricks-ai-workshops/advanced
   ```

2. Validate your configuration (checks for errors in `databricks.yml`):
   ```bash
   databricks bundle validate -t dev
   ```
   If this prints errors, go back to Step 5 and fix the placeholders.

3. Deploy the bundle (uploads code and registers the app):
   ```bash
   databricks bundle deploy -t dev
   ```

4. Start the app:
   ```bash
   databricks apps start retail-grocery-ltm-memory
   ```

5. Wait for the app to reach RUNNING state (first startup takes 3-5 minutes):
   ```bash
   databricks apps get retail-grocery-ltm-memory --output json | jq -r '.status.state'
   ```
   Repeat until it shows `RUNNING`.

6. Deploy the source code to the running app:
   ```bash
   DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
   databricks apps deploy retail-grocery-ltm-memory \
     --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/.bundle/retail_grocery_ltm_memory/dev/files
   ```

---

## Step 7: Grant Permissions

The app runs as a service principal that needs access to your resources.

### Get the service principal ID

```bash
SP_CLIENT_ID=$(databricks apps get retail-grocery-ltm-memory --output json | jq -r '.service_principal_client_id')
echo "App SP Client ID: $SP_CLIENT_ID"
```

### Grant Unity Catalog access

Run in the SQL Editor or a notebook:

```sql
GRANT USE CATALOG ON CATALOG <your-catalog> TO `<SP_CLIENT_ID>`;
GRANT USE SCHEMA ON SCHEMA <your-catalog>.<your-schema> TO `<SP_CLIENT_ID>`;
GRANT SELECT ON SCHEMA <your-catalog>.<your-schema> TO `<SP_CLIENT_ID>`;
```

### Grant Genie Space access

1. In the left sidebar, go to your **Genie Space**
2. Click **Share** (top-right)
3. Add the service principal (search by client ID) with **Can Run** permission

### Grant Lakebase access (if needed)

If you see "permission denied" errors related to Lakebase, run the permission script from the Web Terminal:

```bash
cd /Workspace/Repos/<your-username>/databricks-ai-workshops/advanced
pip install databricks-sdk
python scripts/grant_lakebase_permissions.py "$SP_CLIENT_ID" \
  --memory-type langgraph-short-term --project <project-name> --branch <branch-name>
python scripts/grant_lakebase_permissions.py "$SP_CLIENT_ID" \
  --memory-type langgraph-long-term --project <project-name> --branch <branch-name>
```

---

## Step 8: Verify the Deployment

### Check app status

1. In the left sidebar, go to **Compute** > **Apps**
2. Find your app — the status dot should turn green and show **Running**
3. If it shows **Starting**, wait a few more minutes (it's installing dependencies)
4. If it shows **Crashed**, see the Troubleshooting section below

### Check logs (if something seems wrong)

1. Click your app name > go to the **Logs** tab
2. Look for these lines that mean everything is working:
   - `"Uvicorn running on http://0.0.0.0:8000"` — backend is ready
   - `"Server is running on http://localhost:3000"` — frontend is ready

### Test the app

1. Click the **app URL** (shown at the top of the app page) to open the chat interface
2. Try these test prompts:

| Prompt | What it tests |
|--------|---------------|
| "What are the top 5 products by revenue?" | Genie Space (structured data queries) |
| "What is the return policy for perishable items?" | Vector Search (policy document retrieval) |
| "Remember that I prefer organic products" | Long-term memory (store preference) |
| "What are my preferences?" (in a new chat) | Long-term memory (recall preference) |

If the agent responds with relevant answers, you're done!

---

## Troubleshooting

| What you see | What went wrong | How to fix it |
|---|---|---|
| `databricks bundle validate` shows errors | Typo or unreplaced placeholder in YAML | Read the error — it usually points to the exact line. Check all values from Steps 2-4 are filled in |
| App shows **Crashed** | Usually a config issue | Click app > Logs tab > scroll to the error |
| `unhandled errors in a TaskGroup` | GENIE_SPACE_ID or VECTOR_SEARCH_INDEX is invalid | Verify the Genie Space ID and VS index name match Step 2 output exactly |
| `permission denied for schema` | Service principal can't access Lakebase | Re-run Step 7 (Lakebase permissions section) |
| `relation "ai_chatbot"."Chat" already exists` | Database tables were created manually | Drop them: `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` then restart app |
| Agent doesn't use tools | Wrong resource IDs in config | Verify Genie Space ID and VS index in `databricks.yml` match Step 2 output |
| Vector Search returns no results | Index hasn't finished syncing | Wait 5-10 minutes after Step 2. Check sync status in Catalog Explorer > find your index > Sync tab |
| `Cannot deploy app... not in RUNNING state` | App must be started before deploying source code | Run `databricks apps start retail-grocery-ltm-memory` and wait for RUNNING state |
| `UniqueViolation` on first startup | Race condition in table creation | Safe to ignore — handled automatically on retry |

---

## Architecture

```
┌───────────────────── Databricks Workspace ─────────────────────────┐
│                                                                     │
│  ┌────────────────────────────┐                                    │
│  │ 01_quickstart_setup.py     │                                    │
│  │ (Data Setup - Step 2)      │                                    │
│  │                            │                                    │
│  │ Creates:                   │                                    │
│  │  • UC tables (6)           │                                    │
│  │  • policy_docs_chunked     │                                    │
│  │  • Vector Search index ────┼───┐                                │
│  │  • Genie Space ────────────┼───┼───┐                            │
│  │  • MLflow Experiment ──────┼───┼───┼───┐                        │
│  └────────────────────────────┘   │   │   │                        │
│                                   │   │   │                        │
│  ┌────────────────────────────────┼───┼───┼──────────────────────┐ │
│  │  Databricks App               │   │   │                      │ │
│  │  (deployed via bundle)        │   │   │                      │ │
│  │                               ▼   ▼   ▼                      │ │
│  │  ┌──────────────────────────────────────────────────────┐    │ │
│  │  │ agent_server (Python, port 8000)                     │    │ │
│  │  │  • LangGraph agent with MCP tools                    │    │ │
│  │  │  • Connects to VS index and Genie via MCP            │    │ │
│  │  │  • Logs traces to MLflow Experiment                  │    │ │
│  │  │  • Long-term memory (user prefs, tasks, history)     │    │ │
│  │  └──────────────────────────────────────────────────────┘    │ │
│  │  ┌──────────────────────────────────────────────────────┐    │ │
│  │  │ e2e-chatbot-app-next (Node.js, port 3000)           │    │ │
│  │  │  • Chat UI with persistent history                   │    │ │
│  │  │  • Auto-creates ai_chatbot tables (Drizzle)          │    │ │
│  │  └──────────────────────────────────────────────────────┘    │ │
│  └───────────────────────────────┬───────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Lakebase (Managed PostgreSQL)                    │  │
│  │                                                              │  │
│  │  langgraph_memory      │  ai_chatbot      │  drizzle         │  │
│  │  (checkpoints, user    │  (Chat, Message,  │  (migration      │  │
│  │   prefs, tasks - auto) │   Vote - auto)    │   tracking)      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary: What You Create vs. What the App Creates

| Resource | Who creates it | When | Do you need to do anything? |
|---|---|---|---|
| Data tables + Vector Search + Genie | You | Step 2 (run notebook) | Yes — run the notebook |
| MLflow Experiment | You | Step 2 (notebook creates it) | Just note the ID |
| Lakebase instance | You | Step 3 (create in UI) | Yes — create in UI |
| The deployed App itself | You | Step 6 (deploy commands) | Yes — deploy it |
| Agent memory tables | The app | Automatically at first startup | No — hands off! |
| Chat history tables | The app | Automatically at first startup | No — hands off! |
| Database permissions | Not needed | — | The app owns its own tables |
