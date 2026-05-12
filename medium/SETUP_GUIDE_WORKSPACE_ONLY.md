# Workshop Setup Guide: Deploy Agent App (Workspace Only)

This guide walks you through deploying an AI agent app **entirely from within a Databricks workspace** — no local machine setup, no terminal installations needed on your laptop.

By the end, you'll have a working chat application powered by an AI agent that can search documents and query data.

---

## Prerequisites

Before you start, confirm your Databricks workspace has these features enabled (ask your workspace admin if unsure):

- **Unity Catalog** — for organizing data tables and permissions
- **Databricks Apps** — for hosting the chat application
- **Lakebase** — managed PostgreSQL database (used for chat history)
- **Web Terminal** — an in-browser terminal (Settings → Developer → Web Terminal)
- A **running SQL warehouse** — needed to create data tables (Compute → SQL Warehouses → check one is running)

---

## Step 1: Import the Repository into Your Workspace

This brings the code into your Databricks workspace so you can edit and deploy it.

1. In the left sidebar, click **Workspace** → **Repos** (may also appear as "Git Folders")
2. Click **Add** → **Git Folder**
3. Paste the repository URL and click **Create Git Folder**

Once imported, your code will be at a path like:
`/Workspace/Repos/<your-username>/<repo-name>/`

> **Tip:** You can also use **Import** to upload a zip file, but Git Folder is recommended — it lets you pull updates later.

---

## Step 2: Run the Data Setup Notebook

This notebook creates the sample data and AI tools that your agent will use. Think of it as populating a database with demo data and setting up the search/query services.

1. In the workspace file browser, navigate to `data/workspace_setup_script/01_quickstart_setup.py`
2. Click it to open as a notebook
3. At the top, you'll see two dropdown **widgets** — select your **catalog** and **schema** (these are like a database and folder for organizing your tables)
4. Click **Run All** at the top (takes ~10-15 minutes — most of the wait is Vector Search provisioning)

**What this creates for you:**

| Resource | What it does (in plain terms) |
|----------|-------------------------------|
| 6 data tables | Sample business data (customers, products, transactions, etc.) |
| policy_docs_chunked | Documents split into searchable chunks |
| Vector Search index | Enables the agent to search documents by meaning (not just keywords) |
| Genie Space | Lets the agent answer data questions using natural language → SQL |
| MLflow Experiment | A place to log and monitor your agent's behavior |

**Copy these 4 values from the notebook output — you'll need them in Step 5:**

| What to copy | Looks like | You'll use it in |
|------|---------|---------|
| MLflow Experiment ID | `1234567890123456` | Step 5a (`databricks.yml`) |
| Vector Search Index name | `my_catalog.my_schema.policy_docs_index` | Step 5b (`agent.py`) |
| Genie Space ID | `01abcdef12345678` | Step 5b (`agent.py`) |
| Catalog.Schema | `my_catalog.my_schema` | Step 5b (`agent.py`) |

---

## Step 3: Create a Lakebase Instance

Lakebase is a managed PostgreSQL database inside Databricks. Your app uses it to remember conversations — both for the agent's memory and for the chat interface's message history.

**Create the instance:**

1. In the left sidebar, go to **Compute** → **Lakebase**
2. Click **Create Project** → choose **Autoscaling**
3. Name it something memorable (e.g., `my-agent-workshop`)
4. Click Create — a `production` branch is created automatically
5. Wait ~1-2 minutes for it to show as "Ready"

**Find your connection details (needed for Step 5):**

You need two paths that tell the app where your database lives. To find them:

1. Open the notebook `medium/scripts/lakebase_setup_script.ipynb` in the workspace
2. In **Cell 3**, replace `<project name>` with the project name you just created (e.g., `my-agent-workshop`)
3. Run **Cell 3** — it will print output like:

   ```json
   {
     "databases": [
       { "name": "projects/my-agent-workshop/branches/production/databases/abc123def456" }
     ]
   }
   ```

4. From this output, note:
   - **Branch path**: `projects/my-agent-workshop/branches/production`
   - **Database path**: the full `name` value (e.g., `projects/my-agent-workshop/branches/production/databases/abc123def456`)

> **Important:** Only run Cell 1 (optional, to verify endpoints) and Cell 3 (to find the database ID). **Do NOT run Cells 2, 4, or 5** — the app creates its own database tables automatically when it starts. Creating them manually beforehand will cause errors.

---

## Step 4: Confirm the MLflow Experiment ID

The data setup notebook (Step 2) already created an MLflow experiment for you. You just need to confirm the **Experiment ID** (a number you'll paste into a config file).

**To find it:**
1. In the left sidebar, click **Experiments**
2. Find the experiment created by the notebook (look for the name printed in Step 2's output)
3. Click on it — the **Experiment ID** is the long number in your browser's URL bar (e.g., the `1234567890123456` part of `.../ml/experiments/1234567890123456`)

**If you can't find it or need a new one:**
1. Go to **Experiments** in the left sidebar
2. Click **Create Experiment** (top-right)
3. Give it a name (e.g., `my-agent-experiment`)
4. Click Create — copy the Experiment ID from the URL

---

## Step 5: Edit Configuration Files

You'll edit two files to tell the app about YOUR workspace resources. Navigate to the `medium/` folder in the workspace file browser.

### 5a. Edit `databricks.yml`

This file tells Databricks how to deploy your app and what resources it needs. Open it and find-and-replace these 5 placeholders:

| Find this in the file | Replace with | Where you got it |
|---|---|---|
| `"my-agent-app"` | A unique name for your app (e.g., `"agent-workshop-jsmith"`) | Choose your own |
| `"<your-experiment-id>"` | The number from Step 4 (e.g., `"1234567890123456"`) | Step 4 |
| `"projects/<your-project>/branches/<branch-name>"` | Your branch path (e.g., `"projects/my-agent-workshop/branches/production"`) | Step 3 |
| `"projects/<your-project>/branches/<branch-name>/databases/<your-database-id>"` | Your full database path (e.g., `"projects/my-agent-workshop/branches/production/databases/abc123"`) | Step 3 |
| `https://<your-workspace>.cloud.databricks.com` | Your workspace URL (copy from your browser's address bar) | Browser |

> **Tip:** The app name must be unique across your workspace. Adding your initials helps avoid conflicts (e.g., `agent-workshop-jsmith`).

**Here's what the key sections should look like after your edits:**

```yaml
resources:
  apps:
    agent_openai_agents_sdk:
      name: "agent-workshop-jsmith"        # ← your unique app name
      # ... (leave the env vars section unchanged) ...
      resources:
        - name: 'experiment'
          experiment:
            experiment_id: "1234567890123456"   # ← from Step 4
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
  prod:
    mode: production
    workspace:
      host: https://my-workspace.cloud.databricks.com   # ← same URL
    resources:
      apps:
        agent_openai_agents_sdk:
          name: agent-workshop-jsmith                    # ← same app name (no quotes here)
```

### 5b. Edit `agent_server/agent.py`

This file defines what your agent can do — its name, personality, and which tools it has access to. Open it and find the configuration section (around line 40):

```python
NAME = 'my-workshop-agent'
SYSTEM_PROMPT = 'You are a helpful assistant with access to data and documents.'
MODEL = 'databricks-claude-sonnet-4-6'  # or your preferred model
MCP_SERVERS = [
    ('Policy Document Search', '/api/2.0/mcp/vector-search/<catalog>/<schema>/<index-name>'),
    ('Data Query Assistant', '/api/2.0/mcp/genie/<genie-space-id>'),
]
```

Replace the two placeholders in `MCP_SERVERS` using values from Step 2:

| Placeholder | Replace with | Example |
|---|---|---|
| `<catalog>/<schema>/<index-name>` | Your Vector Search Index name, with dots replaced by slashes | `my_catalog/my_schema/policy_docs_index` |
| `<genie-space-id>` | Your Genie Space ID | `01abcdef12345678` |

> **Note on the URL format:** If your index name from Step 2 was `my_catalog.my_schema.policy_docs_index` (with dots), change the dots to slashes in the URL: `my_catalog/my_schema/policy_docs_index`

---

## Step 6: Deploy the App

Now you'll deploy your configured app to Databricks. Choose **one** of the two methods below:

- **Path A (Recommended):** Use the Web Terminal — 3 commands and you're done
- **Path B:** Use the graphical Apps UI — click-based, no terminal needed

---

### Path A: Deploy via Web Terminal (Recommended)

This uses a built-in terminal in your browser to run 3 commands.

#### What happens automatically

When the app starts, it creates its own database tables — you don't need to set anything up in the database. Specifically it creates:

- Chat history tables (for the UI sidebar)
- Agent memory tables (so the agent remembers conversation context)
- A migration tracking table (internal bookkeeping)

> **Do NOT manually create database tables before deploying.** If you previously ran any database setup cells (Cells 2/4/5 of `lakebase_setup_script.ipynb`), you need to clean up first:
> ```sql
> -- Run this in a notebook connected to your Lakebase instance:
> DROP SCHEMA IF EXISTS ai_chatbot CASCADE;
> DROP SCHEMA IF EXISTS drizzle CASCADE;
> DROP SCHEMA IF EXISTS agent_openai_memory CASCADE;
> ```

#### Deploy steps

1. Open the **Web Terminal**: click the `>_` terminal icon in the bottom panel of your workspace, or go to Settings → Developer → Web Terminal

2. Navigate to the `medium` folder:
   ```bash
   cd /Workspace/Repos/<your-username>/<repo-name>/medium
   ```

3. Validate your configuration (checks for errors in `databricks.yml`):
   ```bash
   databricks bundle validate
   ```
   If this prints errors, go back to Step 5a and fix the placeholders.

4. Deploy the app:
   ```bash
   databricks bundle deploy
   ```
   This uploads your code and registers the app with Databricks (~30 seconds).

5. Start the app:
   ```bash
   databricks bundle run agent_openai_agents_sdk
   ```
   This triggers the app to actually start running. First startup takes **3-5 minutes** (it installs dependencies and creates database tables).

> **What's the difference between deploy and run?** `deploy` uploads your code and configuration. `run` starts (or restarts) the app. You'll use `deploy` + `run` together whenever you make changes.

---

### Path B: Deploy via Apps UI (No Terminal)

Use this if you prefer clicking through a graphical interface or don't have Web Terminal access.

The same rule applies: the app creates its own database tables automatically — do NOT create them manually beforehand.

#### Deploy steps

1. In the left sidebar, go to **Compute** → **Apps** → click **Create App**

2. Fill in the basics:
   - **Name**: The app name you chose in Step 5a (e.g., `agent-workshop-jsmith`)
   - **Source code path**: `/Workspace/Repos/<your-username>/<repo-name>/medium`
   - **Command**: `uv run start-app`

3. Add these **Environment Variables** (click "Add Variable" for each):

   | Variable | Value | Notes |
   |---|---|---|
   | `MLFLOW_TRACKING_URI` | `databricks` | Tells the agent where to log traces |
   | `MLFLOW_REGISTRY_URI` | `databricks-uc` | Model registry location |
   | `API_PROXY` | `http://localhost:8000/invocations` | Internal routing (don't change) |
   | `CHAT_APP_PORT` | `3000` | Frontend port (don't change) |
   | `CHAT_PROXY_TIMEOUT_SECONDS` | `300` | How long to wait for agent responses |
   | `LAKEBASE_AGENT_MEMORY_SCHEMA` | `agent_openai_memory` | Database schema name for memory |
   | `PGDATABASE` | `databricks_postgres` | Database name (don't change) |
   | `PGPORT` | `5432` | Database port (don't change) |

4. Add two variables with **"Value From Resource"** (these get their values automatically from the resources you'll configure next):
   - `MLFLOW_EXPERIMENT_ID` → value from resource named `experiment`
   - `LAKEBASE_AUTOSCALING_ENDPOINT` → value from resource named `postgres`

5. Add **Resources** (scroll down to the Resources section):
   - Click **Add Resource** → **Experiment**:
     - Resource name: `experiment`
     - Experiment ID: your ID from Step 4
     - Permission: `CAN_MANAGE`
   - Click **Add Resource** → **Postgres**:
     - Resource name: `postgres`
     - Branch: your branch path from Step 3 (e.g., `projects/my-agent-workshop/branches/production`)
     - Database: your database path from Step 3 (e.g., `projects/my-agent-workshop/branches/production/databases/abc123`)
     - Permission: `CAN_CONNECT_AND_CREATE`

6. Click **Create** (or **Deploy**)

#### If the app crashes with "permission denied" errors

This means the app's service account couldn't create database tables. Fix it by running the setup notebook cells:

1. Open `medium/scripts/lakebase_setup_script.ipynb`
2. Run **Cell 2** — creates agent memory tables
3. Uncomment and run **Cell 4** — creates chat history tables
4. Uncomment and run **Cell 5** — grants access permissions

Then tell the app that these tables already exist by running this SQL (in a notebook connected to your Lakebase):

```sql
CREATE SCHEMA IF NOT EXISTS drizzle;
CREATE TABLE IF NOT EXISTS drizzle.__drizzle_migrations (
    id SERIAL PRIMARY KEY,
    hash text NOT NULL,
    created_at bigint
);

INSERT INTO drizzle.__drizzle_migrations (hash, created_at) VALUES
('d88ae3f9c87a8e04af8da37f8d061672231d1bf063aa8c3d4af7442b82f34a04', 1761818298417),
('c69141f027d6bf7cfd735224d36cb0f3b046de256cc509a1105a513ffc3cbc4b', 1740268800000),
('9570d343c8a61e9181fdbc00e0c9fe67a36b77ab038baab53226a4d5228b48d8', 1772346540471);
```

Then restart the app from the Apps UI.

---

## Step 7: Verify the Deployment

### Check app status (wait 3-5 minutes for first startup)

1. In the left sidebar, go to **Compute** → **Apps**
2. Find your app — the status dot should turn green and show **Running**
3. If it shows **Starting**, wait a few more minutes (it's installing dependencies)
4. If it shows **Crashed**, see the Troubleshooting section below

### Check logs (if something seems wrong)

1. Click your app name → go to the **Logs** tab
2. Scroll to the bottom — look for these lines that mean everything is working:
   - `"Uvicorn running on http://0.0.0.0:8000"` — backend is ready
   - `"Server is running on http://localhost:3000"` — frontend is ready

### Test the app

1. Click the **app URL** (shown at the top of the app page) to open the chat interface
2. Try sending: "What tools do you have?" — the agent should list its available tools
3. Try a document question: "What is the refund policy?" — tests Vector Search
4. Try a data question: "How many customers do we have?" — tests the Genie Space

If the agent responds with relevant answers, you're done!

---

## Troubleshooting

| What you see | What went wrong | How to fix it |
|---|---|---|
| `relation "ai_chatbot"."Chat" already exists` | You created database tables manually before deploying | Drop them and restart: run `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` in a notebook connected to Lakebase, then restart the app |
| `permission denied for schema` | The app can't access tables you created | Same fix as above — drop schemas and let the app recreate them (it will own them this time) |
| App shows **"Crashed"** | Usually a typo in `databricks.yml` | Click your app → Logs tab → scroll to the error. Most common: a placeholder like `<your-project>` wasn't replaced |
| `Lakebase unavailable` | Wrong database path in config | Double-check the `branch:` and `database:` values in `databricks.yml` match what Cell 3 printed in Step 3 |
| Agent doesn't use tools / "I don't have access to..." | Wrong URL in `agent.py` | Verify the catalog/schema/index in the URL matches Step 2 output. Remember: dots become slashes (`my_catalog.my_schema.index` → `my_catalog/my_schema/index`) |
| `An app with the same name already exists` | Someone else deployed with the same name | Choose a different name in `databricks.yml`, or delete the old one: `databricks apps delete <name>` in Web Terminal |
| Chat sidebar shows no history after refresh | Database migration failed silently | Check logs for `"❌ Database migration failed"` — usually means tables existed already (see first row) |
| `databricks bundle validate` shows errors | Syntax error or unreplaced placeholder in YAML | Read the error message carefully — it usually points to the exact line. Check that all `<...>` placeholders are replaced |
| Vector Search returns no results | Index hasn't finished syncing | Wait 5-10 minutes after Step 2 completes. You can check sync status in Catalog Explorer → find your index → check the Sync tab |

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
│  │  (deployed via bundle/UI)     │   │   │                      │ │
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
| The deployed App itself | You | Step 6 (deploy command or UI) | Yes — deploy it |
| Chat history tables | The app | Automatically at first startup | No — hands off! |
| Agent memory tables | The app | Automatically at first startup | No — hands off! |
| Database permissions | Not needed | — | No — the app owns its own tables |
