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

**Authenticate the CLI before starting:**
```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile DEFAULT
databricks current-user me  # verify it works
```

## Placeholders

Replace these throughout the workshop:

| Placeholder | Example |
|-------------|---------|
| `<CATALOG>` | `my_catalog` |
| `<SCHEMA>` | `retail_agent` |
| `<WAREHOUSE-ID>` | from `databricks warehouses list` |
| `<PROJECT-NAME>` | `retail-grocery-agent` (Lakebase autoscaling project) |
| `<BRANCH-NAME>` | `production` (Lakebase autoscaling branch) |
| `<GENIE-SPACE-ID>` | `01ef...abcd` (from Genie URL) |
| `<EXPERIMENT-ID>` | `1159599289265540` |

---

## Step 1: Clone the Repo

```bash
git clone https://github.com/AnanyaDBJ/databricks-ai-workshops.git
cd databricks-ai-workshops
```

---

## Step 2: Create Catalog and Schema

Run in the Databricks SQL Editor:

```sql
CREATE CATALOG IF NOT EXISTS <CATALOG>;
CREATE SCHEMA IF NOT EXISTS <CATALOG>.<SCHEMA>;
```

---

## Step 3: Generate Structured Data

```bash
cd data
```

Edit `execute_sql.py` — set `CATALOG` and `SCHEMA` on lines 19-20, then run:

```bash
python execute_sql.py --profile DEFAULT --warehouse-id <WAREHOUSE-ID>
```

This creates 6 tables: customers, products, stores, transactions, transaction_items, payment_history.

---

## Step 4: Generate Policy Document Chunks

Edit `execute_chunking.py` — set `CATALOG` and `SCHEMA` on lines 18-19, then run:

```bash
python execute_chunking.py --profile DEFAULT --warehouse-id <WAREHOUSE-ID>
```

This chunks 7 policy docs and writes to the `policy_docs_chunked` table.

---

## Step 5: Create a Vector Search Endpoint

In the Databricks UI: **Compute > Vector Search > Create Endpoint**

- Name: `freshmart-policies`
- Wait for status: **READY** (~5-10 min)

---

## Step 6: Create a Vector Search Index

In **Catalog Explorer**, navigate to `<CATALOG>.<SCHEMA>.policy_docs_chunked`:

1. Click **Create > Vector Search Index**
2. Set: name=`policy_docs_index`, primary key=`chunk_id`, endpoint=from Step 5, source column=`content`, model=`databricks-gte-large-en`, sync=Triggered
3. Click **Create**

Note the full path: `<CATALOG>.<SCHEMA>.policy_docs_index`

---

## Step 7: Create a Genie Space

In the Databricks UI: **Genie > New Genie Space**

1. Name: `Retail Grocery Data`
2. Add all 6 tables from your schema
3. Select a SQL warehouse and click **Create**
4. Copy the **Space ID** from the URL

---

## Step 8: Create a Lakebase Autoscaling Instance

```bash
# Create the project
databricks api post /api/2.0/postgres/projects --json '{
  "name": "<PROJECT-NAME>"
}'

# Create the branch
databricks api post /api/2.0/postgres/projects/<PROJECT-NAME>/branches --json '{
  "name": "<BRANCH-NAME>"
}'

# Verify the endpoint is ACTIVE
databricks api get /api/2.0/postgres/projects/<PROJECT-NAME>/branches/<BRANCH-NAME>/endpoints \
  | jq '.endpoints[0].status.current_state'
# Wait until "ACTIVE"
```

Get the PGHOST for later:
```bash
databricks api get /api/2.0/postgres/projects/<PROJECT-NAME>/branches/<BRANCH-NAME>/endpoints \
  | jq -r '.endpoints[0].status.hosts.host'
```

---

## Step 9: Create an MLflow Experiment

```bash
cd ../advanced
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks experiments create --name "/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory"
```

Copy the returned `experiment_id`.

---

## Step 10: Register the System Prompt

```bash
uv run register-prompt --name <CATALOG>.<SCHEMA>.freshmart_system_prompt
```

---

## Step 11: Grant Permissions

### Lakebase

For autoscaling Lakebase, permissions are managed via Databricks identity — no manual `psql` role creation needed. Your Databricks user is automatically authenticated via OAuth when connecting.

### Genie Space

**Genie > your space > Share** > Add your user with **Can Run**.

### Vector Search Index

**Catalog Explorer > your index > Permissions** > Add your user with **SELECT**.

### MLflow Experiment

**Experiments > your experiment > Permissions** > Add your user with **Can Manage**.

### Unity Catalog

```sql
GRANT USE CATALOG ON CATALOG <CATALOG> TO `your.email@company.com`;
GRANT USE SCHEMA ON SCHEMA <CATALOG>.<SCHEMA> TO `your.email@company.com`;
GRANT SELECT ON SCHEMA <CATALOG>.<SCHEMA> TO `your.email@company.com`;
```

---

## Step 12: Configure Environment Variables

```bash
cd advanced
cp .env.example .env
```

Edit `.env`:

```bash
DATABRICKS_CONFIG_PROFILE=DEFAULT
MLFLOW_EXPERIMENT_ID=<EXPERIMENT-ID>
LAKEBASE_AUTOSCALING_PROJECT=<PROJECT-NAME>
LAKEBASE_AUTOSCALING_BRANCH=<BRANCH-NAME>
GENIE_SPACE_ID=<GENIE-SPACE-ID>
VECTOR_SEARCH_INDEX=<CATALOG>.<SCHEMA>.policy_docs_index
PROMPT_REGISTRY_NAME=<CATALOG>.<SCHEMA>.freshmart_system_prompt
PGHOST=<your-lakebase-hostname>
PGUSER=your.email@company.com
PGDATABASE=databricks_postgres
```

To find your Lakebase hostname (from Step 8):
```bash
databricks api get /api/2.0/postgres/projects/<PROJECT-NAME>/branches/<BRANCH-NAME>/endpoints \
  | jq -r '.endpoints[0].status.hosts.host'
```

---

## Step 13: Run Locally

```bash
uv run start-app
```

This starts the backend on `http://localhost:8000` and the chat UI on `http://localhost:3000`.

Open `http://localhost:3000` and try these prompts:

- "What are the top 5 products by revenue?" (Genie)
- "What is the return policy for perishable items?" (Vector Search)
- "Remember that I prefer organic products" then in a new chat: "What are my preferences?" (Memory)

Verify traces in **Experiments > your experiment** in the Databricks UI.

---

## Step 14: Configure Deployment Files

### `databricks.yml` — Update resource definitions

Set your actual resource IDs in the `resources` section:

```yaml
        - name: "experiment"
          experiment:
            experiment_id: "<EXPERIMENT-ID>"
            permission: "CAN_MANAGE"
        - name: "retail_grocery_genie"
          genie_space:
            name: "Retail Grocery Data"
            space_id: "<GENIE-SPACE-ID>"
            permission: "CAN_RUN"
        - name: "lakebase_memory"
          database:
            autoscaling_project: "<PROJECT-NAME>"
            autoscaling_branch: "<BRANCH-NAME>"
            database_name: "databricks_postgres"
            permission: "CAN_CONNECT_AND_CREATE"
        - name: "policy_docs_index"
          uc_securable:
            securable_full_name: "<CATALOG>.<SCHEMA>.policy_docs_index"
            securable_type: "TABLE"
            permission: "SELECT"
```

Set the prompt registry value:
```yaml
          - name: PROMPT_REGISTRY_NAME
            value: "<CATALOG>.<SCHEMA>.freshmart_system_prompt"
```

---

## Step 15: Deploy to Databricks Apps

```bash
# Validate
databricks bundle validate -t dev

# Deploy
databricks bundle deploy -t dev

# Deploy source code to the app
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks apps deploy retail-grocery-ltm-memory \
  --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/.bundle/retail_grocery_ltm_memory/dev/files
```

---

## Step 16: Grant App Service Principal Permissions

```bash
# Get the app's service principal
SP_CLIENT_ID=$(databricks apps get retail-grocery-ltm-memory --output json | jq -r '.service_principal_client_id')

# Grant Lakebase permissions
uv run python scripts/grant_lakebase_permissions.py "$SP_CLIENT_ID" \
  --memory-type langgraph-short-term --project <PROJECT-NAME> --branch <BRANCH-NAME>
uv run python scripts/grant_lakebase_permissions.py "$SP_CLIENT_ID" \
  --memory-type langgraph-long-term --project <PROJECT-NAME> --branch <BRANCH-NAME>
```

Also grant the SP access to the Genie Space: **Genie > your space > Share** > Add the service principal with **Can Run**.

---

## Step 17: Start and Verify the App

```bash
databricks apps start retail-grocery-ltm-memory

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

Open the app URL in your browser and try the same prompts from Step 13.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `relation "store" does not exist` | Memory tables not created — restart the app, it auto-creates on first request |
| App stuck in `STOPPED` | `databricks apps start retail-grocery-ltm-memory` |
| `302` error on API call | Use OAuth token (`databricks auth token`), not a PAT |
| Lakebase permission denied | Re-run Step 16 (deployed). For local: verify CLI auth is valid (`databricks auth token`) |
| `bundle validate` fails | Check `value_from` names match resource `name` fields exactly |
| Vector Search returns empty | Verify the index has data in Catalog Explorer |
| Local app Lakebase error | Check PGHOST/PGUSER in `.env`. If token expired, restart app after `databricks auth login` |
| Genie permission error | Grant Can Run to your user (Step 11) or app SP (Step 16) |
| View app logs | **Apps > retail-grocery-ltm-memory > Logs** or `databricks apps get-logs retail-grocery-ltm-memory` |
