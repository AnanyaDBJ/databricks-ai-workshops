# Workshop: Deploy AI Agent with Memory (Workspace Only)

This guide walks you through deploying the L200 AI agent app **entirely from within a Databricks workspace** — no local machine setup, no terminal installations needed on your laptop.

By the end, you'll have a working chat application powered by an AI agent that can search documents and query data.

---

## Prerequisites

Before you start, confirm your Databricks workspace has these features enabled (ask your workspace admin if unsure):

- **Unity Catalog** — for organizing data tables and permissions
- **Databricks Apps** — for hosting the chat application
- **Lakebase** — managed PostgreSQL database (used for agent memory + chat history)
- **Web Terminal** — an in-browser terminal (Settings > Developer > Web Terminal)
- A **running SQL warehouse** — needed to create data tables (Compute > SQL Warehouses)

---

## Step 1: Import the Repository into Your Workspace

1. In the left sidebar, click **Workspace** > **Repos** (may also appear as "Git Folders")
2. Click **Add** > **Git Folder**
3. Paste the repository URL: `https://github.com/AnanyaDBJ/databricks-ai-workshops.git`
4. Click **Create Git Folder**

Once imported, your code will be at a path like:
`/Workspace/Repos/<your-username>/databricks-ai-workshops/`

---

## Step 2: Set Up Your Data

Complete **Path B (Workspace Notebook)** from [`data/README.md`](../data/README.md#path-b-workspace-notebook).

1. Navigate to `data/workspace_setup_script/01_quickstart_setup.py`
2. Select your **catalog** and **schema** in the dropdown widgets
3. Click **Run All** (takes ~10-15 minutes)

**Copy these 4 values from the notebook output — you'll need them in Step 5:**

| What to copy | Looks like | You'll use it in |
|------|---------|---------|
| MLflow Experiment ID | `1234567890123456` | Step 5a (`databricks.yml`) |
| Vector Search Index name | `my_catalog.my_schema.policy_docs_index` | Step 5b (`agent.py`) |
| Genie Space ID | `01abcdef12345678` | Step 5b (`agent.py`) |
| Catalog.Schema | `my_catalog.my_schema` | Step 5b (`agent.py`) |

---

## Step 3: Create a Lakebase Instance

Lakebase is a managed PostgreSQL database inside Databricks. Your app uses it for agent memory and chat history.

### Create the instance

1. In the left sidebar, go to **Compute** > **Lakebase**
2. Click **Create Project** > choose **Autoscaling**
3. Name it something memorable (e.g., `my-agent-workshop`)
4. Click Create — a `production` branch is created automatically
5. Wait ~1-2 minutes for it to show as "Ready"

### Find your connection details

1. Open the notebook `medium/scripts/lakebase_setup_script.ipynb` in the workspace
2. In **Cell 3**, replace `<project name>` with the project name you just created
3. Run **Cell 3** — note the output:
   - **Branch path**: `projects/my-agent-workshop/branches/production`
   - **Database path**: the full `name` value (e.g., `projects/my-agent-workshop/branches/production/databases/abc123def456`)

> **Important:** Only run Cell 1 (optional) and Cell 3. Do NOT run Cells 2, 4, or 5 — the app creates its own database tables automatically.

---

## Step 3 (Alternative): Using a Lakebase Provisioned Instance

If your workspace uses a **Provisioned** Lakebase instance (instead of Autoscaling):

1. Go to **Compute** > **Lakebase** > **Create** > **Provisioned**
2. Name it (e.g., `my-agent-workshop`), select capacity `CU_1`, click Create
3. Wait for it to show as "Running"

The only value you need is the **instance name** (e.g., `my-agent-workshop`).

When you get to Step 5a, use these different configurations:

```yaml
# Replace the postgres resource with:
        - name: 'database'
          database:
            database_name: databricks_postgres
            instance_name: 'my-agent-workshop'
            permission: CAN_CONNECT_AND_CREATE

# Replace LAKEBASE_AUTOSCALING_ENDPOINT env var with:
          - name: LAKEBASE_INSTANCE_NAME
            value: "my-agent-workshop"
```

---

## Step 4: Confirm the MLflow Experiment ID

The data setup notebook (Step 2) already created an MLflow experiment. Confirm the **Experiment ID**:

1. In the left sidebar, click **Experiments**
2. Find the experiment created by the notebook
3. Click on it — the **Experiment ID** is the long number in your browser's URL bar

**If you can't find it or need a new one:**
1. Go to **Experiments** > **Create Experiment** (top-right)
2. Give it a name (e.g., `my-agent-experiment`)
3. Click Create — copy the Experiment ID from the URL

---

## Step 5: Edit Configuration Files

Navigate to the `medium/` folder in the workspace file browser.

### 5a. Edit `databricks.yml`

Find-and-replace these values:

| Find this | Replace with | Where you got it |
|---|---|---|
| `"my-agent-app"` | A unique name (e.g., `"agent-workshop-jsmith"`) | Choose your own |
| `"<your-experiment-id>"` | Your Experiment ID (e.g., `"1234567890123456"`) | Step 4 |
| `"projects/<your-project>/branches/<branch-name>"` | Your branch path | Step 3 |
| `"projects/<your-project>/branches/<branch-name>/databases/<your-database-id>"` | Your database path | Step 3 |
| `https://<your-workspace>.cloud.databricks.com` | Your workspace URL | Browser address bar |

**Here's what the key sections should look like after edits:**

```yaml
resources:
  apps:
    agent_openai_agents_sdk:
      name: "agent-workshop-jsmith"                    # ← your unique app name
      # ... (leave env vars section unchanged) ...
      resources:
        - name: 'experiment'
          experiment:
            experiment_id: "1234567890123456"           # ← from Step 4
            permission: 'CAN_MANAGE'
        - name: 'postgres'
          postgres:
            branch: "projects/my-agent-workshop/branches/production"         # ← from Step 3
            database: "projects/my-agent-workshop/branches/production/databases/abc123"  # ← from Step 3
            permission: 'CAN_CONNECT_AND_CREATE'

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://my-workspace.cloud.databricks.com   # ← your workspace URL
```

### 5b. Edit `agent_server/agent.py`

Find the `MCP_SERVERS` configuration and replace the placeholders:

```python
MCP_SERVERS = [
    ('Policy Document Search', '/api/2.0/mcp/vector-search/<catalog>/<schema>/<index-name>'),
    ('Data Query Assistant', '/api/2.0/mcp/genie/<genie-space-id>'),
]
```

| Placeholder | Replace with | Example |
|---|---|---|
| `<catalog>/<schema>/<index-name>` | Your Vector Search Index (dots → slashes) | `my_catalog/my_schema/policy_docs_index` |
| `<genie-space-id>` | Your Genie Space ID | `01abcdef12345678` |

---

## Step 6: Deploy the App

Open the **Web Terminal**: click the `>_` terminal icon in the bottom panel, or go to Settings > Developer > Web Terminal.

1. Navigate to the `medium` folder:
   ```bash
   cd /Workspace/Repos/<your-username>/databricks-ai-workshops/medium
   ```

2. Validate your configuration:
   ```bash
   databricks bundle validate
   ```
   If this prints errors, go back to Step 5a and fix the placeholders.

3. Deploy the app:
   ```bash
   databricks bundle deploy
   ```

4. Start the app:
   ```bash
   databricks bundle run agent_openai_agents_sdk
   ```
   First startup takes **3-5 minutes** (installing dependencies and creating database tables).

---

## Step 7: Verify the Deployment

### Check app status

1. In the left sidebar, go to **Compute** > **Apps**
2. Find your app — the status dot should turn green and show **Running**
3. If it shows **Starting**, wait a few more minutes
4. If it shows **Crashed**, see Troubleshooting below

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
| "What is the refund policy?" | Vector Search (document retrieval) |
| "How many customers do we have?" | Genie Space (data queries) |
| "Remember my name is Alice" | Agent memory (store) |
| "What's my name?" (after refresh) | Agent memory (recall) |

If the agent responds with relevant answers, you're done!

---

## Troubleshooting

| What you see | What went wrong | How to fix it |
|---|---|---|
| `relation "ai_chatbot"."Chat" already exists` | Database tables created manually before deploy | Drop schemas: `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` then restart app |
| `permission denied for schema` | App can't access tables you created | Drop schemas and let the app recreate them (it will own them) |
| App shows **Crashed** | Usually a typo in `databricks.yml` | Click app > Logs tab > scroll to the error |
| `Lakebase unavailable` | Wrong database path in config | Verify `branch:` and `database:` in `databricks.yml` match Cell 3 output |
| Agent doesn't use tools | Wrong URL in `agent.py` | Verify catalog/schema/index matches Step 2. Dots become slashes in URLs |
| `An app with the same name already exists` | Name collision | Choose a different name or delete: `databricks apps delete <name>` |
| `databricks bundle validate` shows errors | Unreplaced placeholder in YAML | Read the error — it points to the exact line |
| Vector Search returns no results | Index hasn't finished syncing | Wait 5-10 minutes after Step 2 |

---

## Architecture

![L200 Architecture](./L200_Architecture.png)

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
│  │  │  • Connects to VS index and Genie via MCP            │    │ │
│  │  │  • Logs traces to MLflow Experiment                  │    │ │
│  │  │  • Auto-creates agent_openai_memory tables           │    │ │
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
│  │  agent_openai_memory    │  ai_chatbot      │  drizzle        │  │
│  │  (agent conversation    │  (Chat, User,    │  (migration     │  │
│  │   memory - auto)        │   Message, Vote  │   journal -     │  │
│  │                         │   - auto)        │   auto)         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary: What You Create vs. What the App Creates

| Resource | Who creates it | When | Do you need to do anything? |
|---|---|---|---|
| Data tables + Vector Search + Genie Space | You | Step 2 (run the notebook) | Yes — run the notebook |
| MLflow Experiment | You | Step 2 (notebook creates it) | Just note the ID |
| Lakebase database instance | You | Step 3 (click Create in UI) | Yes — create in UI |
| The deployed App itself | You | Step 6 (deploy command) | Yes — deploy it |
| Chat history tables | The app | Automatically at first startup | No — hands off! |
| Agent memory tables | The app | Automatically at first startup | No — hands off! |
| Database permissions | Not needed | — | No — the app owns its own tables |
