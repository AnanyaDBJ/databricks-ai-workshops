# Workshop: Deploying a Retail Grocery AI Agent as a Databricks App

This guide walks you through configuring and deploying the **Retail Grocery AI Agent** — a conversational agent with Genie (structured data), Vector Search (policy docs), and long-term memory (Lakebase) — as a Databricks App.

---

## Prerequisites

Before you begin, ensure you have:

- [ ] **Databricks CLI** installed and authenticated (`databricks auth login`)
- [ ] **uv** (Python package manager) installed — [install guide](https://docs.astral.sh/uv/getting-started/installation/)
- [ ] **Node.js 20+** installed (for the chat UI)
- [ ] Access to a Databricks workspace with the following already provisioned:
  - A **Genie Space** with your retail data tables
  - A **Lakebase instance** (provisioned)
  - A **Vector Search index** with chunked policy documents

You should have these values ready:

| Value | Example | Where to find it |
|-------|---------|-------------------|
| Genie Space ID | `01ef...abcd` | Genie UI > your space > URL contains the ID |
| Lakebase instance name | `my-lakebase-instance` | Catalog Explorer > Databases |
| Vector Search index path | `my_catalog.my_schema.policy_docs_index` | Catalog Explorer > your index |
| Catalog and schema | `my_catalog.my_schema` | Unity Catalog > your catalog and schema |

---

## Step 1: Update `app.yaml` — Environment Variable Injection

Open `advanced/app.yaml`. The environment variables for Genie, Lakebase, and Vector Search use `valueFrom` to reference resources defined in `databricks.yml`. This means values are **injected automatically** by the Databricks Apps platform at runtime — you don't hardcode them here.

Verify your `app.yaml` looks like this (no changes needed if it already does):

```yaml
  - name: MLFLOW_EXPERIMENT_ID
    valueFrom: experiment
  - name: LAKEBASE_INSTANCE_NAME
    valueFrom: lakebase_memory
  - name: GENIE_SPACE_ID
    valueFrom: retail_grocery_genie
  - name: VECTOR_SEARCH_INDEX
    valueFrom: policy_docs_index
  - name: PROMPT_REGISTRY_NAME
    valueFrom: system_prompt
```

> **How `valueFrom` works:** Each name (e.g., `lakebase_memory`) references a resource defined in `databricks.yml`. At deploy time, the platform resolves the resource and injects the appropriate value (hostname, space ID, etc.) into the environment variable.

---

## Step 2: Update `databricks.yml` — Resource Definitions

Open `advanced/databricks.yml`. This file defines the Databricks Asset Bundle — the app, its environment, and the resources it needs.

### 2a. Update the env section to use `value_from`

In the `config.env` section (around lines 23-33), ensure the three resource-backed variables use `value_from` (not hardcoded `value`):

```yaml
        env:
          # ... static env vars above ...
          - name: MLFLOW_EXPERIMENT_ID
            value_from: "experiment"
          - name: LAKEBASE_INSTANCE_NAME
            value_from: "lakebase_memory"
          - name: GENIE_SPACE_ID
            value_from: "retail_grocery_genie"
          - name: VECTOR_SEARCH_INDEX
            value_from: "policy_docs_index"
          - name: PROMPT_REGISTRY_NAME
            value_from: "system_prompt"
```

> **Note:** `databricks.yml` uses `value_from` (underscore). `app.yaml` uses `valueFrom` (camelCase). Both are correct — they're different file formats.

### 2b. Fill in your resource values

In the `resources` section (around lines 36-59), replace the placeholder values with your actual resource IDs:

**Genie Space** (line 46):
```yaml
        - name: "retail_grocery_genie"
          genie_space:
            name: "Retail Grocery Data"
            space_id: "<YOUR-GENIE-SPACE-ID>"
            permission: "CAN_RUN"
```

**Lakebase** (line 51):
```yaml
        - name: "lakebase_memory"
          database:
            instance_name: "<YOUR-LAKEBASE-INSTANCE-NAME>"
            database_name: "databricks_postgres"
            permission: "CAN_CONNECT_AND_CREATE"
```

**Vector Search Index** (line 57):
```yaml
        - name: "policy_docs_index"
          uc_securable:
            securable_full_name: "<YOUR-CATALOG>.<YOUR-SCHEMA>.<YOUR-INDEX-NAME>"
            securable_type: "TABLE"
            permission: "SELECT"
```

**Prompt Registry** (system prompt in Unity Catalog):
```yaml
        - name: "system_prompt"
          uc_securable:
            securable_full_name: "<YOUR-CATALOG>.<YOUR-SCHEMA>.freshmart_system_prompt"
            securable_type: "FUNCTION"
            permission: "EXECUTE"
```

> **Important:** The `securable_full_name` uses **dots** (e.g., `my_catalog.my_schema.policy_docs_index`), not slashes.

---

## Step 3: Register the System Prompt

The agent loads its system prompt from the Databricks Prompt Registry (Unity Catalog). Register it by running:

```bash
cd advanced
uv run register-prompt --name <YOUR-CATALOG>.<YOUR-SCHEMA>.freshmart_system_prompt
```

This registers the FreshMart system prompt in Unity Catalog and sets a `@production` alias. The agent loads the prompt at startup via the `PROMPT_REGISTRY_NAME` environment variable.

> **Tip:** To update the prompt later, create a new version in the Catalog Explorer UI and move the `@production` alias — no code changes needed.

---

## Step 4: Create an MLflow Experiment

The app uses MLflow for tracing and evaluation. Create an experiment in your workspace:

```bash
cd advanced

# Get your Databricks username
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)

# Create the experiment
databricks experiments create \
  --name "/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory"
```

Copy the returned `experiment_id` (a numeric string like `620...`) and paste it into `databricks.yml` line 40:

```yaml
        - name: "experiment"
          experiment:
            experiment_id: "<PASTE-YOUR-EXPERIMENT-ID>"
            permission: "CAN_MANAGE"
```

---

## Step 5: Validate the Bundle

Before deploying, validate that your configuration is correct:

```bash
cd advanced
databricks bundle validate -t dev
```

If you see errors, fix them before proceeding. Common issues:
- Mismatched resource names between `value_from` and the resource `name` fields
- Invalid experiment ID format
- Missing Databricks CLI authentication

---

## Step 6: Deploy the App

Deploy using Databricks Asset Bundles:

```bash
databricks bundle deploy -t dev
```

This command will:
1. Create the app `retail-grocery-ltm-memory` in your workspace
2. Upload all source code
3. Bind the resources (experiment, Genie space, Lakebase, Vector Search index)
4. Configure the environment variables via `valueFrom`

After the bundle deploys, you need to deploy the source code to the app:

```bash
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks apps deploy retail-grocery-ltm-memory \
  --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/.bundle/retail_grocery_ltm_memory/dev/files
```

---

## Step 7: Grant Lakebase Permissions

After deployment, the app gets assigned a **service principal**. This SP needs database permissions to create the memory tables.

```bash
# Get the app's service principal client ID
SP_CLIENT_ID=$(databricks apps get retail-grocery-ltm-memory --output json | jq -r '.service_principal_client_id')

echo "Service Principal Client ID: $SP_CLIENT_ID"

# Grant permissions for short-term memory (conversation state)
uv run python scripts/grant_lakebase_permissions.py "$SP_CLIENT_ID" \
  --memory-type langgraph-short-term \
  --instance-name <YOUR-LAKEBASE-INSTANCE-NAME>

# Grant permissions for long-term memory (user preferences, task history)
uv run python scripts/grant_lakebase_permissions.py "$SP_CLIENT_ID" \
  --memory-type langgraph-long-term \
  --instance-name <YOUR-LAKEBASE-INSTANCE-NAME>
```

> **Note:** Replace `<YOUR-LAKEBASE-INSTANCE-NAME>` with your actual instance name (e.g., `my-lakebase-instance`).

---

## Step 8: Start the App

After deployment, the app may be in a stopped state. Start it:

```bash
databricks apps start retail-grocery-ltm-memory
```

Wait for the app to reach `RUNNING` state. You can check status with:

```bash
databricks apps get retail-grocery-ltm-memory
```

---

## Step 9: Verify the Deployment

### Get the app URL

```bash
APP_URL=$(databricks apps get retail-grocery-ltm-memory --output json | jq -r '.url')
echo "App URL: $APP_URL"
```

### Test the agent API

```bash
# Get an OAuth token
TOKEN=$(databricks auth token | jq -r .access_token)

# Send a test message
curl -X POST "${APP_URL}/invocations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "What stores do you have?"}]}'
```

### Open the Chat UI

Navigate to the app URL in your browser. You should see the chat interface.

Try these test prompts:
- **Genie (structured data):** "What are the top 5 products by revenue?"
- **Vector Search (policy docs):** "What is the return policy for perishable items?"
- **Memory:** "Remember that I prefer organic products" → then in a new conversation: "What are my preferences?"

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| App stuck in `STOPPED` state | Run `databricks apps start retail-grocery-ltm-memory` |
| `302` error when calling the API | Use an OAuth token (`databricks auth token`), not a PAT |
| Permission denied on Lakebase | Re-run Step 7 (Grant Lakebase Permissions) with the correct SP client ID |
| `bundle validate` fails | Check that all `value_from` names match the resource `name` fields exactly |
| Vector Search returns empty results | Verify the index exists and has data in Catalog Explorer |
| App logs show missing env vars | Check `app.yaml` `valueFrom` names match `databricks.yml` resource names |
| App won't start after bundle deploy | Run the `databricks apps deploy` command from Step 6 to deploy source code |

### Viewing App Logs

In the Databricks UI: **Apps** > **retail-grocery-ltm-memory** > **Logs**

Or via CLI:

```bash
databricks apps get-logs retail-grocery-ltm-memory
```

---

## Reference: How `valueFrom` Maps to Resources

```
app.yaml (valueFrom)          databricks.yml (resource name)       Injected Value
─────────────────────          ──────────────────────────────       ──────────────
experiment              ───►   experiment                     ───► experiment ID
lakebase_memory         ───►   lakebase_memory (database)     ───► Lakebase hostname
retail_grocery_genie    ───►   retail_grocery_genie           ───► Genie space ID
policy_docs_index       ───►   policy_docs_index              ───► securable_full_name (dot format)
system_prompt           ───►   system_prompt (uc_securable)   ───► securable_full_name (prompt name)
```
