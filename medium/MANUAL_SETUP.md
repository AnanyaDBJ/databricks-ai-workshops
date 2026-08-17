# Manual Setup — L200 Agent (fallback runbook)

**Use this when the setup scripts don't work in your environment.** Workshop workspaces
differ, and `uv run quickstart` / `configure-agent` / `grant-all` occasionally fail on
missing tooling, permissions, or SDK versions. This runbook reproduces **every step the
scripts perform**, by hand, so you can get to a working app either way.

Each section maps to one script/phase. You can do the whole thing manually, or drop down
here only for the step that failed and go back to the automated flow afterward — the
phases are independent.

| Phase | Script it replaces | Section |
|---|---|---|
| Auth & profile | `quickstart` (part) | [Authentication & profile](#authentication--profile) |
| Experiment, Lakebase, config files | `quickstart` | [Lakebase & config (quickstart)](#lakebase--config-quickstart) |
| Tool wiring | `configure-agent` | [Configure the agent (configure-agent)](#configure-the-agent-configure-agent) |
| Local run | `start-app` / `preflight` | [Run locally](#run-locally) |
| Deploy | (manual anyway) | [Deploy](#deploy) |
| Permissions | `grant-all` | [Grant permissions (grant-all)](#grant-permissions-grant-all) |

> **Local vs Workspace:** run the shell commands below in your **laptop terminal** (local
> path) or the Databricks **Web Terminal** (workspace path). Where they differ, both are
> shown. In the Web Terminal, first `cd /Workspace/Repos/<you>/databricks-ai-workshops/medium`.

---

## Authentication & profile

Replaces the auth portion of `quickstart`.

```bash
# Local: log in and create a CLI profile named DEFAULT
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile DEFAULT
databricks auth profiles          # verify it lists as VALID
```

In the Web Terminal you're already authenticated as yourself — no profile needed; omit
`--profile` from every command below.

Create `.env` from the template and set the profile:

```bash
cp .env.example .env
```

Edit `.env` and set (leave the rest as-is for now):

```env
DATABRICKS_CONFIG_PROFILE=DEFAULT
MLFLOW_TRACKING_URI="databricks"
MLFLOW_REGISTRY_URI="databricks-uc"
```

---

## Lakebase & config (quickstart)

Replaces `quickstart`'s experiment creation, Lakebase creation, and edits to `.env` +
`databricks.yml`.

### 1. MLflow experiment

Use the Experiment ID from the data setup, or create one:

1. Left sidebar → **Experiments** → **Create Experiment** → name it → **Create**
2. Copy the **Experiment ID** (the long number in the URL).

Set it in `.env`:

```env
MLFLOW_EXPERIMENT_ID=<your-experiment-id>
```

### 2. Create the Lakebase instance

**Autoscaling (default):**

1. Left sidebar → **Compute** > **Lakebase** → **Create Project** → **Autoscaling**
2. Name it (e.g. `my-agent-workshop`) → **Create**. A `production` branch is created.
3. Wait for **Ready** (~1–2 min).

**Provisioned (alternative):** **Compute** > **Lakebase** > **Create** > **Provisioned**,
name it, capacity `CU_1`, **Create**, wait for **Running**. You only need the instance name.

### 3. Find connection details (autoscaling)

Open `scripts/lakebase_setup_script.ipynb`, run **Cell 1** (pip install), put your project
name in **Cell 4**, run it, and note:
- **Branch path**: `projects/<project>/branches/production`
- **Database path**: the full `name`, e.g. `projects/<project>/branches/production/databases/databricks-postgres`
- **Endpoint host** (`PGHOST`) if shown.

> Only run the read-only cells. The app creates its own tables — don't run table-creation cells.

### 4. Fill `.env`

Autoscaling:

```env
LAKEBASE_AUTOSCALING_ENDPOINT=projects/<project>/branches/production/endpoints/<endpoint>
LAKEBASE_AGENT_MEMORY_SCHEMA=agent_openai_memory
PGHOST=<your-lakebase-hostname>
PGDATABASE=databricks_postgres
PGPORT=5432
PGUSER=<your-email@company.com>
```

Provisioned — replace the endpoint line with:

```env
LAKEBASE_INSTANCE_NAME=my-agent-workshop
```

### 5. Fill `databricks.yml`

Set the app name, experiment, workspace host, and Lakebase resource:

```yaml
resources:
  apps:
    agent_openai_agents_sdk:
      name: "agent-<your-app-name>"                 # unique app name
      resources:
        - name: 'experiment'
          experiment:
            experiment_id: "<your-experiment-id>"
            permission: 'CAN_MANAGE'
        - name: 'postgres'                          # autoscaling
          postgres:
            branch: "projects/<project>/branches/production"
            database: "projects/<project>/branches/production/databases/databricks-postgres"
            permission: 'CAN_CONNECT_AND_CREATE'

targets:
  dev:
    workspace:
      host: https://<your-workspace>.cloud.databricks.com
```

Provisioned variant — replace the `postgres` resource with:

```yaml
        - name: 'database'
          database:
            database_name: databricks_postgres
            instance_name: 'my-agent-workshop'
            permission: CAN_CONNECT_AND_CREATE
```

and in the app `env:` block use `LAKEBASE_INSTANCE_NAME` instead of `LAKEBASE_AUTOSCALING_ENDPOINT`.

---

## Configure the agent (configure-agent)

Replaces `configure-agent`. Edit the `# GENERATED` block in `agent_server/agent.py`
(laptop editor, or the workspace file editor). Change **only** what's between the markers.

```python
# GENERATED

NAME = 'retail-agent'
SYSTEM_PROMPT = 'You are a retail store operations assistant. Use the available tools to answer questions about policies and data.'
MODEL = os.environ.get('AGENT_MODEL', DEFAULT_MODEL)   # leave this line as-is (env-driven)
MCP_SERVERS = [
    ('Vector Search: <catalog>.<schema>.<index>', '/api/2.0/mcp/vector-search/<catalog>/<schema>/<index>'),
    ('Genie Space: <name>', '/api/2.0/mcp/genie/<genie-space-id>'),
]

# END GENERATED
```

**Building the MCP URLs — the copy-paste the script normally does for you:**

| Tool | Your value | URL to paste |
|---|---|---|
| Vector Search index | `my_catalog.my_schema.policy_docs_index` | `/api/2.0/mcp/vector-search/my_catalog/my_schema/policy_docs_index` |
| Genie space | id `01abcdef12345678` | `/api/2.0/mcp/genie/01abcdef12345678` |
| UC functions (schema) | `my_catalog.my_schema` | `/api/2.0/mcp/functions/my_catalog/my_schema` |

> **Rule:** in the Vector Search URL, the index's dots become slashes.

To see what exists in your workspace: `uv run discover-tools` (or `--profile DEFAULT`).

**Model routing** — set in `.env`, not `agent.py` (the `MODEL` line stays env-driven):

```env
AGENT_MODEL=databricks-claude-opus-4-6
AGENT_USE_AI_GATEWAY=false
```

For the AI Gateway exercise, set `AGENT_USE_AI_GATEWAY=true` **and** point `AGENT_MODEL`
at your gateway endpoint (often `catalog.schema.endpoint`). The two are coupled: `true`
routes to `{host}/ai-gateway/mlflow/v1` (gateway endpoint name), `false` routes to
`{host}/serving-endpoints` (serving endpoint name). A mismatch fails at request time.

---

## Run locally

Replaces `start-app` / `preflight`.

```bash
uv run start-app          # backend :8000 + frontend :3000, creates DB tables on first run
```

Open `http://localhost:3000` and try a Vector Search question, a Genie question, and a
memory question ("Remember my name is Alice" → refresh → "What's my name?").

No `uv`? Start the backend directly:

```bash
python -m agent_server.start_server
```

---

## Deploy

Manual anyway — same in both guides. From the project root (Web Terminal: after `cd`):

```bash
databricks bundle validate                              # add --profile DEFAULT locally
databricks bundle deploy
databricks bundle run agent_openai_agents_sdk
```

**Workspace only:** before `bundle run`, remove the terraform binaries or the app source
snapshot exceeds its 50MB limit:

```bash
rm -rf .databricks/bundle/dev/bin .databricks/bundle/dev/terraform/.terraform
```

**App already exists?** Bind instead of recreating:

```bash
databricks bundle deployment bind agent_openai_agents_sdk <app-name> --auto-approve
databricks bundle deploy
```

---

## Grant permissions (grant-all)

Replaces `grant-all`. Three independent grants — do whichever the script couldn't.

### 1. Get the app's service principal id

UI: **Compute** > **Apps** > your app → copy the **Service Principal** client id. Or:

```bash
databricks apps get <your-app-name> --output json | jq -r '.service_principal_client_id'
# add --profile DEFAULT locally
```

### 2. Lakebase grants

Connect to your Lakebase instance (psql, a notebook, or any Postgres client) and run:

```sql
-- Agent memory schema
GRANT USAGE ON SCHEMA agent_openai_memory TO PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA agent_openai_memory TO PUBLIC;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA agent_openai_memory TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA agent_openai_memory GRANT ALL ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA agent_openai_memory GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO PUBLIC;

-- Chat history schema
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

> Some tables don't exist until the app's first request. If grants on missing tables fail,
> that's expected — re-run after the first request. The `TO PUBLIC` form above avoids the
> per-SP role step; alternatively, use `uv run python scripts/grant_lakebase_permissions.py
> <sp-client-id> --memory-type openai --autoscaling-endpoint <endpoint>` which grants to the
> SP role specifically.

### 3. Unity Catalog grants

In the **SQL Editor** (or a notebook on your SQL warehouse), with your catalog/schema and
the SP id from step 1:

```sql
GRANT USE CATALOG ON CATALOG <your-catalog> TO `<SP_CLIENT_ID>`;
GRANT USE SCHEMA ON SCHEMA <your-catalog>.<your-schema> TO `<SP_CLIENT_ID>`;
GRANT SELECT ON SCHEMA <your-catalog>.<your-schema> TO `<SP_CLIENT_ID>`;
```

### 4. Genie "Can Run"

1. Left sidebar → your **Genie Space** (from the data setup)
2. **Share** (top-right)
3. Search for the service principal by client id or name
4. Grant **Can Run**

---

## Verify

- **Compute** > **Apps** → status should be green / **Running**.
- App > **Logs** → `Uvicorn running on http://0.0.0.0:8000` and `Server is running on http://localhost:3000`.
- Open the app URL and test Vector Search, Genie, and memory prompts.

If the agent answers with relevant, tool-grounded responses, you're done.
