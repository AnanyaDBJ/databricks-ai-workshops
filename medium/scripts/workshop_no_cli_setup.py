# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Workshop Setup — No CLI
# MAGIC %md
# MAGIC # Deploy AI Agent App — No CLI Setup
# MAGIC
# MAGIC **Run this notebook end-to-end** to deploy the L200 AI agent app entirely from within Databricks — no CLI, no Web Terminal, no local machine.
# MAGIC
# MAGIC ## What this notebook does
# MAGIC
# MAGIC | Step | Action |
# MAGIC |------|--------|
# MAGIC | 1 | Install dependencies |
# MAGIC | 2 | Discover your Lakebase connection details |
# MAGIC | 3 | Create/find your MLflow experiment |
# MAGIC | 4 | Configure `agent_server/agent.py` with your tools |
# MAGIC | 5 | Configure `databricks.yml` with your resources |
# MAGIC | 6 | Create and deploy the Databricks App |
# MAGIC | 7 | Configure access for the app's service principal |
# MAGIC | 8 | Verify the deployment |
# MAGIC
# MAGIC ## Prerequisites
# MAGIC
# MAGIC - **Data setup complete** — you've already run `data/workspace_setup_script/01_quickstart_setup` and have your catalog, schema, Vector Search index, and Genie space ready.
# MAGIC - **Lakebase project created** — via Compute > Lakebase > Create Project > Autoscaling.
# MAGIC - **SQL warehouse running** — for executing UC permission statements.
# MAGIC
# MAGIC **Fill in the widgets above, then click Run All.**

# COMMAND ----------

# DBTITLE 1,Step 1: Install Dependencies
# MAGIC %pip install "databricks-sdk>=0.70.0" "databricks-ai-bridge>=0.5.0" mlflow
# MAGIC %restart_python

# COMMAND ----------

# Create parameter widgets
try:
    dbutils.widgets.text("app_name", "", "App Name")
    dbutils.widgets.text("lakebase_project", "", "Lakebase Project Name")
    dbutils.widgets.text("catalog", "", "Unity Catalog Name")
    dbutils.widgets.text("schema", "", "Schema Name")
    dbutils.widgets.text("vs_index", "", "Vector Search index (name only, or catalog.schema.index)")
    dbutils.widgets.text("genie_space_id", "", "Genie Space ID")
    dbutils.widgets.text("experiment_id", "", "Experiment ID (optional)")
    dbutils.widgets.text("agent_name", "AI Agent Assistant", "Agent Display Name")
    dbutils.widgets.text("system_prompt", "You are a helpful AI assistant.", "System Prompt")
    dbutils.widgets.text("ai_gateway_endpoint", "", "AI Gateway Endpoint (optional)")
    print("✓ Configuration widgets created at the top of the notebook")
except Exception as e:
    # Widgets may already exist from a previous run
    if "already exists" not in str(e).lower():
        raise
    print("✓ Configuration widgets already exist")

print("\n" + "="*60)
print("NEXT STEP: Fill in the required widget values above, then run this cell again.")
print("="*60)

# COMMAND ----------

# DBTITLE 1,Configuration Widgets

# Read parameter values (set via the parameter widgets at the top of the notebook)
APP_NAME = dbutils.widgets.get("app_name").strip()
LAKEBASE_PROJECT = dbutils.widgets.get("lakebase_project").strip()
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
VS_INDEX = dbutils.widgets.get("vs_index").strip()
GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id").strip()
EXPERIMENT_ID = dbutils.widgets.get("experiment_id").strip()
AGENT_NAME = dbutils.widgets.get("agent_name").strip()
SYSTEM_PROMPT = dbutils.widgets.get("system_prompt").strip()

# Validate required fields
missing = []
if not APP_NAME: missing.append("App Name")
if not LAKEBASE_PROJECT: missing.append("Lakebase Project Name")
if not CATALOG: missing.append("Unity Catalog Name")
if not SCHEMA: missing.append("Schema Name")
if not VS_INDEX: missing.append("Vector Search Index")
if not GENIE_SPACE_ID: missing.append("Genie Space ID")

if missing:
    print("\n⚠ Missing required values:")
    for m in missing:
        print(f"  - {m}")
    print("\nFill in the widgets above, then re-run this cell.")
    dbutils.notebook.exit("Configuration incomplete - please fill in the required widgets")

# Derive paths
import os
_nb_path = dbutils.entry_point.getDbutils().notebook().getContext().notebookPath().get()
# This notebook is at medium/scripts/workshop_no_cli_setup — project root is 2 levels up
PROJECT_ROOT = "/Workspace" + "/".join(_nb_path.split("/")[:-2])
SOURCE_CODE_PATH = PROJECT_ROOT

print("\n" + "="*60)
print("✓ Configuration validated successfully")
print("="*60)
print(f"App Name:          {APP_NAME}")
print(f"Lakebase Project:  {LAKEBASE_PROJECT}")
print(f"Catalog.Schema:    {CATALOG}.{SCHEMA}")
print(f"VS Index:          {VS_INDEX}")
print(f"Genie Space ID:    {GENIE_SPACE_ID}")
print(f"Project Root:      {PROJECT_ROOT}")

# COMMAND ----------

# DBTITLE 1,Re-read widget values after restart
# Read widget values, validate, and init SDK
import os

APP_NAME = dbutils.widgets.get("app_name").strip()
LAKEBASE_PROJECT = dbutils.widgets.get("lakebase_project").strip()
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
VS_INDEX = dbutils.widgets.get("vs_index").strip()
GENIE_SPACE_ID = dbutils.widgets.get("genie_space_id").strip()
EXPERIMENT_ID = dbutils.widgets.get("experiment_id").strip()
AGENT_NAME = dbutils.widgets.get("agent_name").strip()
SYSTEM_PROMPT = dbutils.widgets.get("system_prompt").strip()
AI_GATEWAY_ENDPOINT = dbutils.widgets.get("ai_gateway_endpoint").strip()

# Derive gateway settings
USE_AI_GATEWAY = bool(AI_GATEWAY_ENDPOINT)
AGENT_MODEL = AI_GATEWAY_ENDPOINT if USE_AI_GATEWAY else "databricks-claude-opus-4-6"

# Validate
missing = []
if not APP_NAME: missing.append("App Name")
if not LAKEBASE_PROJECT: missing.append("Lakebase Project Name")
if not CATALOG: missing.append("Unity Catalog Name")
if not SCHEMA: missing.append("Schema Name")
if not VS_INDEX: missing.append("Vector Search Index")
if not GENIE_SPACE_ID: missing.append("Genie Space ID")

if missing:
    raise ValueError(
        f"Fill in the following widgets at the top of the notebook, then Run All again: {', '.join(missing)}"
    )

_nb_path = dbutils.entry_point.getDbutils().notebook().getContext().notebookPath().get()
PROJECT_ROOT = "/Workspace" + "/".join(_nb_path.split("/")[:-2])
SOURCE_CODE_PATH = PROJECT_ROOT

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
WORKSPACE_HOST = w.config.host

print(f"Workspace:     {WORKSPACE_HOST}")
print(f"Project root:  {PROJECT_ROOT}")
print(f"App Name:      {APP_NAME}")
print(f"Catalog:       {CATALOG}.{SCHEMA}")
print(f"AI Gateway:    {'enabled -- ' + AI_GATEWAY_ENDPOINT if USE_AI_GATEWAY else 'disabled (direct model call)'}")

# COMMAND ----------

# DBTITLE 1,Step 2: Discover Lakebase Connection Details
import json

# Discover Lakebase branch, endpoint, and database from the project name
print(f"Discovering Lakebase details for project: {LAKEBASE_PROJECT}")
print("=" * 60)

# List branches
branches_resp = w.api_client.do("GET", f"/api/2.0/postgres/projects/{LAKEBASE_PROJECT}/branches")
branches = branches_resp.get("branches", [])
if not branches:
    raise ValueError(f"No branches found for project '{LAKEBASE_PROJECT}'. Is the project name correct?")

# Use the 'production' branch (default)
branch_name = None
for b in branches:
    if "production" in b["name"]:
        branch_name = b["name"]
        break
if not branch_name:
    branch_name = branches[0]["name"]

branch_id = branch_name.split("/branches/")[-1]
print(f"Branch: {branch_name}")

# List endpoints
endpoints_resp = w.api_client.do(
    "GET", f"/api/2.0/postgres/projects/{LAKEBASE_PROJECT}/branches/{branch_id}/endpoints"
)
endpoints = endpoints_resp.get("endpoints", [])
if not endpoints:
    raise ValueError(f"No endpoints found for branch '{branch_id}'. Is Lakebase ready?")

endpoint_info = endpoints[0]
endpoint_name = endpoint_info["name"]
endpoint_host = endpoint_info.get("status", {}).get("host", "")
print(f"Endpoint: {endpoint_name}")
print(f"Host: {endpoint_host}")

# List databases
databases_resp = w.api_client.do(
    "GET", f"/api/2.0/postgres/projects/{LAKEBASE_PROJECT}/branches/{branch_id}/databases"
)
databases = databases_resp.get("databases", [])
db_name = databases[0]["name"] if databases else f"projects/{LAKEBASE_PROJECT}/branches/{branch_id}/databases/databricks-postgres"
print(f"Database: {db_name}")

# Build the values we need
LAKEBASE_BRANCH = f"projects/{LAKEBASE_PROJECT}/branches/{branch_id}"
LAKEBASE_DATABASE = db_name
LAKEBASE_ENDPOINT = endpoint_name.replace(f"projects/{LAKEBASE_PROJECT}/branches/{branch_id}/endpoints/", "")
LAKEBASE_ENDPOINT_FULL = endpoint_name

print("\n" + "=" * 60)
print(f"LAKEBASE_BRANCH:    {LAKEBASE_BRANCH}")
print(f"LAKEBASE_DATABASE:  {LAKEBASE_DATABASE}")
print(f"LAKEBASE_ENDPOINT:  {LAKEBASE_ENDPOINT_FULL}")
print(f"PGHOST:             {endpoint_host}")

# COMMAND ----------

# DBTITLE 1,Step 3: Create or Find MLflow Experiment
import mlflow

mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks-uc")

if EXPERIMENT_ID:
    # User provided an existing experiment ID
    exp = mlflow.get_experiment(EXPERIMENT_ID)
    print(f"Using existing experiment: {exp.name} (ID: {EXPERIMENT_ID})")
else:
    # Create a new experiment
    exp_name = f"/Users/{w.current_user.me().user_name}/agent-workshop-{APP_NAME}"
    try:
        exp = mlflow.get_experiment_by_name(exp_name)
        if exp:
            EXPERIMENT_ID = exp.experiment_id
            print(f"Found existing experiment: {exp_name} (ID: {EXPERIMENT_ID})")
        else:
            EXPERIMENT_ID = mlflow.create_experiment(exp_name)
            print(f"Created new experiment: {exp_name} (ID: {EXPERIMENT_ID})")
    except Exception:
        EXPERIMENT_ID = mlflow.create_experiment(exp_name)
        print(f"Created new experiment: {exp_name} (ID: {EXPERIMENT_ID})")

print(f"\nExperiment ID: {EXPERIMENT_ID}")

# COMMAND ----------

# DBTITLE 1,Step 4: Configure agent_server/agent.py
# Build the MCP server URLs from user inputs.
# Vector Search needs the fully-qualified index (catalog.schema.index). If only a bare name
# (or schema.index) was entered, qualify it with the Catalog + Schema widgets so the MCP URL
# always has the full catalog/schema/index path — otherwise the agent's tool has no schema.
if VS_INDEX.count(".") < 2:
    VS_INDEX = f"{CATALOG}.{SCHEMA}.{VS_INDEX.split('.')[-1]}"
    print(f"Qualified Vector Search index to: {VS_INDEX}")
# Rule: Vector Search dots become slashes in the URL path.
vs_url_path = "/api/2.0/mcp/vector-search/" + VS_INDEX.replace(".", "/")
genie_url_path = f"/api/2.0/mcp/genie/{GENIE_SPACE_ID}"

# Read the current agent.py
agent_py_path = os.path.join(PROJECT_ROOT, "agent_server", "agent.py")
with open(agent_py_path, "r") as f:
    agent_content = f.read()

# Build the new GENERATED block
new_generated_block = f"""# GENERATED

NAME = '{AGENT_NAME}'
SYSTEM_PROMPT = '{SYSTEM_PROMPT}'
MODEL = os.environ.get('AGENT_MODEL', DEFAULT_MODEL)
MCP_SERVERS = [
    ('Vector Search: {VS_INDEX}', '{vs_url_path}'),
    ('Genie Space: {GENIE_SPACE_ID}', '{genie_url_path}'),
]

# END GENERATED"""

# Replace the GENERATED block
import re
pattern = r"# GENERATED.*?# END GENERATED"
updated_content = re.sub(pattern, new_generated_block, agent_content, flags=re.DOTALL)

if updated_content == agent_content:
    raise ValueError("Could not find the # GENERATED ... # END GENERATED block in agent.py")

with open(agent_py_path, "w") as f:
    f.write(updated_content)

print("\u2713 agent_server/agent.py updated")
print(f"  NAME = '{AGENT_NAME}'")
print(f"  MCP_SERVERS:")
print(f"    - Vector Search: {VS_INDEX}")
print(f"    - Genie Space:   {GENIE_SPACE_ID}")

# COMMAND ----------

# DBTITLE 1,Step 5: Configure databricks.yml
import yaml

yml_path = os.path.join(PROJECT_ROOT, "databricks.yml")
with open(yml_path, "r") as f:
    bundle_config = yaml.safe_load(f)

# Update the app name
bundle_config["resources"]["apps"]["agent_openai_agents_sdk"]["name"] = APP_NAME

# Update the resources (experiment + postgres)
resources_list = bundle_config["resources"]["apps"]["agent_openai_agents_sdk"]["resources"]
for res in resources_list:
    if res.get("name") == "experiment":
        res["experiment"]["experiment_id"] = EXPERIMENT_ID
    elif res.get("name") == "postgres":
        res["postgres"]["branch"] = LAKEBASE_BRANCH
        res["postgres"]["database"] = LAKEBASE_DATABASE

# Update AI Gateway / model routing
env_list = bundle_config["resources"]["apps"]["agent_openai_agents_sdk"]["config"]["env"]
for env_var in env_list:
    if env_var["name"] == "AGENT_MODEL":
        env_var["value"] = AGENT_MODEL
    elif env_var["name"] == "AGENT_USE_AI_GATEWAY":
        env_var["value"] = str(USE_AI_GATEWAY).lower()

# Update the target workspace host
for target_name, target_config in bundle_config.get("targets", {}).items():
    if "workspace" in target_config:
        target_config["workspace"]["host"] = WORKSPACE_HOST

# Write back
with open(yml_path, "w") as f:
    yaml.dump(bundle_config, f, default_flow_style=False, sort_keys=False)

print("\u2713 databricks.yml updated")

# ========================================
# Update app.yaml (standalone deploy config)
# ========================================
app_yaml_path = os.path.join(PROJECT_ROOT, "app.yaml")
if os.path.exists(app_yaml_path):
    with open(app_yaml_path, "r") as f:
        app_config = yaml.safe_load(f)
    
    # Update the AGENT_MODEL and AGENT_USE_AI_GATEWAY env vars
    for env_var in app_config.get("env", []):
        if env_var["name"] == "AGENT_MODEL":
            env_var["value"] = AGENT_MODEL
        elif env_var["name"] == "AGENT_USE_AI_GATEWAY":
            env_var["value"] = str(USE_AI_GATEWAY).lower()
    
    # Write back
    with open(app_yaml_path, "w") as f:
        yaml.dump(app_config, f, default_flow_style=False, sort_keys=False)
    
    print("\u2713 app.yaml updated")
else:
    print("\u26a0 app.yaml not found (skipped)")

# Summary
print("\n" + "="*60)
print("Configuration Summary")
print("="*60)
print(f"  App name:      {APP_NAME}")
print(f"  Experiment:    {EXPERIMENT_ID}")
print(f"  Lakebase:      {LAKEBASE_BRANCH}")
print(f"  AI Gateway:    {USE_AI_GATEWAY} (model: {AGENT_MODEL})")
print(f"  Workspace:     {WORKSPACE_HOST}")

# COMMAND ----------

# DBTITLE 1,Step 6a: Create the App
from databricks.sdk.service.apps import (
    App,
    AppResource,
    AppResourcePostgres,
    AppResourcePostgresPostgresPermission,
    AppResourceExperiment,
    AppResourceExperimentExperimentPermission,
)

print(f"Creating app '{APP_NAME}'...")
print("(This may take 1-2 minutes)")

try:
    app = w.apps.create_and_wait(
        app=App(
            name=APP_NAME,
            description="OpenAI Agents SDK agent application",
            resources=[
                AppResource(
                    name="experiment",
                    experiment=AppResourceExperiment(
                        experiment_id=EXPERIMENT_ID,
                        permission=AppResourceExperimentExperimentPermission.CAN_MANAGE,
                    ),
                ),
                AppResource(
                    name="postgres",
                    postgres=AppResourcePostgres(
                        branch=LAKEBASE_BRANCH,
                        database=LAKEBASE_DATABASE,
                        permission=AppResourcePostgresPostgresPermission.CAN_CONNECT_AND_CREATE,
                    ),
                ),
            ],
        )
    )
    print(f"\n\u2713 App created: {app.name}")
    print(f"  Service Principal Client ID: {app.service_principal_client_id}")
except Exception as e:
    if "already exists" in str(e).lower():
        app = w.apps.get(APP_NAME)
        print(f"\u2713 App already exists: {app.name}")
        print(f"  Service Principal Client ID: {app.service_principal_client_id}")
    else:
        raise

SP_CLIENT_ID = app.service_principal_client_id

# COMMAND ----------

# DBTITLE 1,Step 6b: Clean .venv before deploy
# Remove .venv if it exists — it contains symlinks that break SNAPSHOT deploys
# and adds ~655 MB of unnecessary files. The app rebuilds deps from pyproject.toml + uv.lock.
import shutil

venv_path = os.path.join(PROJECT_ROOT, ".venv")
if os.path.exists(venv_path):
    shutil.rmtree(venv_path)
    print("\u2713 Removed .venv/ (not needed for deployment)")
else:
    print("\u2713 No .venv/ found — clean")

# COMMAND ----------

# DBTITLE 1,Step 6b: Deploy the App
from databricks.sdk.service.apps import AppDeployment, AppDeploymentMode

print(f"Deploying app '{APP_NAME}' from: {SOURCE_CODE_PATH}")
print("(This takes 3-5 minutes on first deploy)")

deployment = w.apps.deploy_and_wait(
    app_name=APP_NAME,
    app_deployment=AppDeployment(
        source_code_path=SOURCE_CODE_PATH,
        mode=AppDeploymentMode.SNAPSHOT,
    ),
)
print(f"\n\u2713 Deployment complete")
print(f"  Status:        {deployment.status.state}")
print(f"  Deployment ID: {deployment.deployment_id}")

# COMMAND ----------

# DBTITLE 1,Step 7a: Unity Catalog Access for Service Principal
# MAGIC %sql
# MAGIC -- Step 7a: Give the app's service principal read access to your data tables.
# MAGIC -- Replace the placeholders below with your actual catalog, schema, and SP client ID
# MAGIC -- (printed in Step 6a output above).
# MAGIC
# MAGIC -- GRANT USE CATALOG ON CATALOG ${catalog} TO `<SP_CLIENT_ID from Step 6a>`;
# MAGIC -- GRANT USE SCHEMA ON SCHEMA ${catalog}.${schema} TO `<SP_CLIENT_ID from Step 6a>`;
# MAGIC -- GRANT SELECT ON SCHEMA ${catalog}.${schema} TO `<SP_CLIENT_ID from Step 6a>`;
# MAGIC
# MAGIC -- >>> UNCOMMENT AND RUN the three lines above after replacing <SP_CLIENT_ID> <<<

# COMMAND ----------

# DBTITLE 1,Step 7b: Unity Catalog Access (automated)
# Automatically run the UC access statements for the service principal.
# This uses the Databricks SDK's statement execution API.

from databricks.sdk.service.sql import StatementState

# Find a SQL warehouse to execute statements
warehouses = list(w.warehouses.list())
running = [wh for wh in warehouses if wh.state and wh.state.value == "RUNNING"]
if running:
    warehouse_id = running[0].id
else:
    warehouse_id = warehouses[0].id if warehouses else None

if not warehouse_id:
    print("No SQL warehouse found. Run the SQL statements in Step 7a manually in the SQL Editor.")
else:
    statements = [
        f"GRANT USE CATALOG ON CATALOG {CATALOG} TO `{SP_CLIENT_ID}`",
        f"GRANT USE SCHEMA ON SCHEMA {CATALOG}.{SCHEMA} TO `{SP_CLIENT_ID}`",
        f"GRANT SELECT ON SCHEMA {CATALOG}.{SCHEMA} TO `{SP_CLIENT_ID}`",
    ]
    for stmt in statements:
        try:
            result = w.statement_execution.execute_statement(
                statement=stmt,
                warehouse_id=warehouse_id,
            )
            if result.status and result.status.state == StatementState.SUCCEEDED:
                print(f"\u2713 {stmt[:70]}")
            else:
                print(f"\u26a0 {stmt[:70]} — {result.status}")
        except Exception as e:
            print(f"\u26a0 {stmt[:50]}... — {e}")
    
    print("\n\u2713 Unity Catalog access configured")

# COMMAND ----------

# DBTITLE 1,Step 7c: Lakebase Schema Access
# Configure Lakebase schema access for the app's service principal.
# The app creates schemas (agent_openai_memory, ai_chatbot, drizzle) on first startup.
# These statements ensure the SP can access them.
#
# NOTE: If the app hasn't started yet, some schemas may not exist.
# That's OK — the "ALTER DEFAULT PRIVILEGES" statements cover future tables.
# Re-run this cell after the app has fully started if you see warnings.

from databricks_ai_bridge.lakebase import LakebaseClient

client = LakebaseClient(autoscaling_endpoint=LAKEBASE_ENDPOINT_FULL)

schemas_to_configure = ["agent_openai_memory", "ai_chatbot", "drizzle"]

for schema_name in schemas_to_configure:
    stmts = [
        f"GRANT USAGE ON SCHEMA {schema_name} TO PUBLIC",
        f"GRANT ALL ON ALL TABLES IN SCHEMA {schema_name} TO PUBLIC",
        f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA {schema_name} TO PUBLIC",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT ALL ON TABLES TO PUBLIC",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO PUBLIC",
    ]
    print(f"\nSchema: {schema_name}")
    for stmt in stmts:
        try:
            client.execute(stmt)
            print(f"  \u2713 {stmt[:65]}")
        except Exception as e:
            err = str(e)
            if "does not exist" in err:
                print(f"  \u23ed Skipped (schema not yet created — re-run after first app start)")
                break
            else:
                print(f"  \u26a0 {err[:80]}")

client.close()
print("\n\u2713 Lakebase access configured (or deferred until app creates schemas)")

# COMMAND ----------

# DBTITLE 1,Step 7d: Genie Space Access (Manual)
# MAGIC %md
# MAGIC ## Step 7d: Genie Space — Manual Step
# MAGIC
# MAGIC The Genie "Can Run" permission must be set via the UI:
# MAGIC
# MAGIC 1. Open your **Genie Space** (left sidebar)
# MAGIC 2. Click **Share** (top-right)
# MAGIC 3. Search for the service principal using the **Client ID** printed in Step 6a
# MAGIC 4. Set permission to **Can Run**
# MAGIC
# MAGIC > **Service Principal Client ID:** check the output of Step 6a above.

# COMMAND ----------

# DBTITLE 1,Step 8: Verify Deployment
import time

# Check app status
print("Checking app status...")
app_status = w.apps.get(APP_NAME)

print(f"\nApp: {app_status.name}")
print(f"Status: {app_status.status.state if app_status.status else 'Unknown'}")
print(f"URL: {app_status.url}")
print(f"Service Principal: {app_status.service_principal_client_id}")

if app_status.url:
    print(f"\n{'=' * 60}")
    print(f"\u2713 YOUR APP IS READY!")
    print(f"{'=' * 60}")
    print(f"\nOpen your app: {app_status.url}")
    print(f"\nTest prompts:")
    print(f"  1. 'What is the refund policy?'  (tests Vector Search)")
    print(f"  2. 'How many customers?'          (tests Genie)")
    print(f"  3. 'Remember my name is Alice'    (tests memory)")
    print(f"  4. Refresh, then 'What is my name?' (tests recall)")
else:
    print("\n\u26a0 App URL not available yet. Check Compute > Apps for status.")
    print("  The app may still be starting up (3-5 min on first deploy).")

# COMMAND ----------

# DBTITLE 1,Troubleshooting: Re-run Lakebase access after first app start
# MAGIC %md
# MAGIC ## Troubleshooting
# MAGIC
# MAGIC **If the app crashes with "permission denied for schema":**
# MAGIC - Re-run **Step 7c** above — the schemas now exist after the first startup attempt.
# MAGIC
# MAGIC **If Genie questions fail:**
# MAGIC - Complete **Step 7d** (share the Genie space with the service principal).
# MAGIC
# MAGIC **If the agent doesn't use tools:**
# MAGIC - Verify `agent_server/agent.py` — MCP URLs must use slashes, not dots: `/api/2.0/mcp/vector-search/catalog/schema/index`
# MAGIC
# MAGIC **If deployment fails with snapshot size error:**
# MAGIC - This can happen if `.databricks/` folder was created locally. The SDK SNAPSHOT mode should handle this automatically.
# MAGIC
# MAGIC **To redeploy after code changes:**
# MAGIC - Re-run **Step 6b** only (the deploy cell). It creates a new deployment from the current source.