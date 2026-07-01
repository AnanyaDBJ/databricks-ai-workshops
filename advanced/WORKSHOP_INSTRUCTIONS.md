# Workshop: Build a Retail Grocery AI Agent on Databricks

Build and deploy a conversational AI agent with Genie, Vector Search, and long-term memory.

## Prerequisites

| Tool | Install |
|------|---------|
| Databricks CLI | `brew tap databricks/tap && brew install databricks` |
| uv | [install guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Node.js 20+ | [nodejs.org](https://nodejs.org) |
| jq | `brew install jq` |

Your workspace needs: Serverless compute, Foundation Model API (Claude), Unity Catalog, Vector Search, and Lakebase.

### Data setup (required first)

Complete the data setup before continuing:
**→ [`data/README.md`](../data/README.md) — Path A (Local CLI)**

When done, you should have these values saved:
- **Catalog.Schema** (e.g., `my_catalog.retail_agent`)
- **Vector Search Index** (e.g., `my_catalog.retail_agent.policy_docs_index`)
- **Genie Space ID** (e.g., `01ef...abcd`)

---

## Step 1: Clone the Repo

```bash
git clone https://github.com/AnanyaDBJ/databricks-ai-workshops.git
cd databricks-ai-workshops/advanced
```

---

## Step 2: Run Quickstart

```bash
uv run quickstart
```

This interactive wizard handles:
- Databricks CLI authentication (OAuth login)
- MLflow experiment creation
- Lakebase autoscaling instance creation (project + branch)
- `.env` file configuration (PGHOST, PGUSER, experiment ID, etc.)

Follow the prompts. When done, your `.env` will have Lakebase and MLflow configured.

---

## Step 3: Update `.env` with Resource IDs

Add the values from your data setup to `.env`:

```bash
GENIE_SPACE_ID=<your-genie-space-id>
VECTOR_SEARCH_INDEX=<your-catalog>.<your-schema>.policy_docs_index
```

Your `.env` should now have all required values (from quickstart + data setup).

---

## Step 4: Run Locally

```bash
uv run start-app
```

This starts the backend on `http://localhost:8000` and the chat UI on `http://localhost:3000`.

Open `http://localhost:3000` and try these prompts:

- "What are the top 5 products by revenue?" (Genie — structured data)
- "What is the return policy for perishable items?" (Vector Search — policy docs)
- "Remember that I prefer organic products" then in a new chat: "What are my preferences?" (Memory)

Verify traces in **Experiments > your experiment** in the Databricks UI.

---

## Step 5: Deploy to Databricks Apps

### 5a. Update `databricks.yml`

Edit the `resources` section in `advanced/databricks.yml` with your actual values:

```yaml
      resources:
        - name: "experiment"
          experiment:
            experiment_id: "<EXPERIMENT-ID>"
            permission: "CAN_MANAGE"
        - name: "retail_grocery_genie"
          genie_space:
            name: "Retail Data"
            space_id: "<GENIE-SPACE-ID>"
            permission: "CAN_RUN"
        - name: "postgres"
          postgres:
            branch: "projects/<PROJECT-NAME>/branches/<BRANCH-NAME>"
            database: "projects/<PROJECT-NAME>/branches/<BRANCH-NAME>/databases/databricks-postgres"
            permission: "CAN_CONNECT_AND_CREATE"
        - name: "policy_docs_index"
          uc_securable:
            securable_full_name: "<CATALOG>.<SCHEMA>.policy_docs_index"
            securable_type: "TABLE"
            permission: "SELECT"
```

Also update the Lakebase env vars:
```yaml
          - name: LAKEBASE_AUTOSCALING_PROJECT
            value: "<PROJECT-NAME>"
          - name: LAKEBASE_AUTOSCALING_BRANCH
            value: "<BRANCH-NAME>"
```

To find your database resource path:
```bash
databricks api get /api/2.0/postgres/projects/<PROJECT-NAME>/branches/<BRANCH-NAME>/databases \
  | jq -r '.databases[0].name'
```

### 5b. Validate and Deploy

```bash
# Validate the bundle config
databricks bundle validate -t dev

# Deploy the bundle (creates the app resource)
databricks bundle deploy -t dev

# Start the app (must be RUNNING before deploying source code)
databricks apps start retail-grocery-ltm-memory

# Wait for app to be running
databricks apps get retail-grocery-ltm-memory --output json | jq -r '.status.state'
# Repeat until state is "RUNNING"

# Deploy source code to the running app
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks apps deploy retail-grocery-ltm-memory \
  --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/.bundle/retail_grocery_ltm_memory/dev/files
```

---

## Step 6: Grant App Service Principal Permissions

```bash
# Get the app's service principal
SP_CLIENT_ID=$(databricks apps get retail-grocery-ltm-memory --output json | jq -r '.service_principal_client_id')
echo "App SP Client ID: $SP_CLIENT_ID"
```

Grant the service principal access to:

1. **Lakebase:**
```bash
uv run python scripts/grant_lakebase_permissions.py "$SP_CLIENT_ID" \
  --memory-type langgraph-short-term --project <PROJECT-NAME> --branch <BRANCH-NAME>
uv run python scripts/grant_lakebase_permissions.py "$SP_CLIENT_ID" \
  --memory-type langgraph-long-term --project <PROJECT-NAME> --branch <BRANCH-NAME>
```

2. **Genie Space:** In the UI — **Genie > your space > Share** > Add the service principal with **Can Run**

3. **Unity Catalog tables:** In SQL Editor:
```sql
GRANT USE CATALOG ON CATALOG <CATALOG> TO `<SP_CLIENT_ID>`;
GRANT USE SCHEMA ON SCHEMA <CATALOG>.<SCHEMA> TO `<SP_CLIENT_ID>`;
GRANT SELECT ON SCHEMA <CATALOG>.<SCHEMA> TO `<SP_CLIENT_ID>`;
```

---

## Step 7: Verify the Deployed App

```bash
# Get the URL
APP_URL=$(databricks apps get retail-grocery-ltm-memory --output json | jq -r '.url')
echo "App URL: $APP_URL"

# Test the API
TOKEN=$(databricks auth token | jq -r .access_token)
curl -X POST "${APP_URL}/invocations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "What stores do you have?"}]}'
```

Open the app URL in your browser to use the chat UI.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `JSONDecodeError` in quickstart | Auth expired — run `databricks auth login --profile DEFAULT` |
| `unhandled errors in a TaskGroup` | GENIE_SPACE_ID or VECTOR_SEARCH_INDEX is empty/invalid in `.env` |
| `UniqueViolation` on first run | Safe to ignore — handled automatically on retry |
| App stuck in `STOPPED` | `databricks apps start retail-grocery-ltm-memory` |
| Lakebase permission denied | Re-run Step 6 (deployed) or verify CLI auth is valid (local) |
| Vector Search returns empty | Wait for index sync to complete — check status in Catalog Explorer |
| Local app won't start | Check `lsof -ti :8000` — kill orphan processes |
| View deployed app logs | `databricks apps get-logs retail-grocery-ltm-memory` or **Apps > Logs** in UI |
