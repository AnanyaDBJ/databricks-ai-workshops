# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "1"
# ///
# MAGIC %md
# MAGIC    
# MAGIC # AI Workshop Data Setup
# MAGIC
# MAGIC This notebook creates everything you need for the workshop:
# MAGIC
# MAGIC | Step | What it creates |
# MAGIC |------|----------------|
# MAGIC | 1 | Catalog and schema in Unity Catalog |
# MAGIC | 2 | Industry-specific structured data tables (see **Industry** widget) |
# MAGIC | 3 | Policy documents table (chunked for search) |
# MAGIC | 4 | Vector Search endpoint and index |
# MAGIC | 5 | Genie Space for natural language data queries |
# MAGIC | 6 | MLflow experiment for agent evaluation |
# MAGIC
# MAGIC **Instructions:** Set **Industry**, **Catalog**, and **Schema** in the widgets, then click **Run All**.
# MAGIC
# MAGIC | Industry | Tables | Policy docs |
# MAGIC |----------|--------|-------------|
# MAGIC | `education` | 6 tables (students, courses, campuses, …) | EduPath Academy |
# MAGIC | `retail` | 6 tables (customers, products, stores, …) | FreshMart (`verticals/retail/docs/`) |
# MAGIC | `financial_services` | 6 tables (clients, accounts, trades, …) | Meridian Capital Partners |
# MAGIC
# MAGIC For `financial_services`, real market data (daily prices and company profiles, 29 tickers) ships with the repo as CSVs in `verticals/financial_services/market_data/` and is loaded into `{catalog}.{schema}` automatically — no Marketplace or Delta Sharing access needed.
# MAGIC
# MAGIC > **First run:** the Configuration cell below stops with an error until the widgets are filled in. Fill them, then click **Run All** again — the `%restart_python` above means later cells need the Configuration cell to have run in the same session.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC
# MAGIC Set your catalog and schema names using the widgets above. All workshop resources are created under `{catalog}.{schema}`.

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch 
# MAGIC %restart_python

# COMMAND ----------

import sys

_notebook_path = dbutils.entry_point.getDbutils().notebook().getContext().notebookPath().get()
_data_root = "/Workspace" + "/".join(_notebook_path.split("/")[:-1])
if _data_root not in sys.path:
    sys.path.insert(0, _data_root)

from verticals.base import vs_endpoint_name
from verticals.registry import INDUSTRIES

if "industry" not in dbutils.widgets.getAll():
    dbutils.widgets.dropdown(
        "industry",
        "education",
        list(INDUSTRIES),
        "Industry",
    )
if "catalog" not in dbutils.widgets.getAll():
    dbutils.widgets.text("catalog", "", "Catalog Name")
if "schema" not in dbutils.widgets.getAll():
    dbutils.widgets.text("schema", "", "Schema Name")

INDUSTRY = dbutils.widgets.get("industry")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

if not CATALOG:
    raise ValueError(
        "Fill the Catalog widget at the top of the notebook, then click Run All again — "
        "later cells depend on this cell having run (a NameError on FULL_SCHEMA means it hasn't)."
    )
if not SCHEMA:
    raise ValueError(
        "Fill the Schema widget at the top of the notebook, then click Run All again — "
        "later cells depend on this cell having run (a NameError on FULL_SCHEMA means it hasn't)."
    )

if INDUSTRY not in INDUSTRIES:
    raise ValueError(f"Unknown industry '{INDUSTRY}'. Expected one of: {', '.join(INDUSTRIES)}")
PLANNED_VS_ENDPOINT_NAME = vs_endpoint_name(INDUSTRY, SCHEMA)

FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"
print(f"Industry: {INDUSTRY}")
print(f"Workshop tables: {FULL_SCHEMA}")
print(f"Planned Vector Search endpoint: {PLANNED_VS_ENDPOINT_NAME}")
if INDUSTRY == "financial_services":
    print(f"Market data (bundled CSVs in the repo) will be loaded into {FULL_SCHEMA}.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Catalog and Schema

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}") # Only if you have access to create catalog and want to have a new catalog for the workshop
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FULL_SCHEMA}")
print(f"Catalog '{CATALOG}' and schema '{FULL_SCHEMA}' are ready.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Generate Industry Data Tables
# MAGIC
# MAGIC Uses the `data` package industry module. Table names and semantics depend on the **Industry** widget.

# COMMAND ----------

from lib.generate import generate_workshop_data

workshop = generate_workshop_data(
    industry=INDUSTRY,
    catalog=CATALOG,
    schema=SCHEMA,
    spark=spark,
    seed=42,
)

tables = workshop.tables
print(f"\n{workshop.brand_name}: created tables {tables}")
print(f"Vector Search endpoint for this run: {workshop.vs_endpoint_name}")
print(f"Chunk table for this run: {FULL_SCHEMA}.{workshop.chunk_table_name}")
print(f"Vector Search index for this run: {FULL_SCHEMA}.{workshop.doc_index_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Documents and Chunked Table
# MAGIC
# MAGIC Reads markdown from `verticals/<industry>/docs/` (retail/education: policies; financial_services: market-shock news), then chunks into an industry-appropriate table name.

# COMMAND ----------

from lib.chunking import chunk_markdown_docs_to_table

chunk_dir = workshop.docs_dir
print(f"Source docs directory: {chunk_dir}")
chunk_markdown_docs_to_table(spark, FULL_SCHEMA, chunk_dir, target_table=workshop.chunk_table_name)

# COMMAND ----------

# MAGIC %md
# MAGIC    
# MAGIC ## Step 4: Create Vector Search Endpoint and Index
# MAGIC
# MAGIC Vector Search lets you find relevant policy documents using natural language instead of exact keyword matches.
# MAGIC This creates:
# MAGIC 1. A **Vector Search endpoint** (the compute that powers similarity search)
# MAGIC 2. A **Delta Sync index** on the policy docs table (automatically generates embeddings)
# MAGIC
# MAGIC The endpoint takes 5-10 minutes to become ready. The cell will wait automatically.

# COMMAND ----------

import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (
    DeltaSyncVectorIndexSpecRequest,
    EmbeddingSourceColumn,
    EndpointType,
    PipelineType,
    VectorIndexType,
)

from lib.workspace_links import (
    notebook_org_id,
    print_asset_link,
    vector_search_endpoint_url,
    vector_search_index_catalog_url,
    vector_search_index_url_from_api,
    workspace_host,
)

w = WorkspaceClient()
WORKSPACE_HOST = workspace_host(w)
WORKSPACE_ORG_ID = notebook_org_id(dbutils)

VS_ENDPOINT_NAME = workshop.vs_endpoint_name
VS_INDEX_NAME = f"{FULL_SCHEMA}.{workshop.doc_index_name}"

# --- Create endpoint (or reuse existing) ---
try:
    endpoint = w.vector_search_endpoints.get_endpoint(VS_ENDPOINT_NAME)
    print(f"Vector Search endpoint '{VS_ENDPOINT_NAME}' already exists (status: {endpoint.endpoint_status.state.value})")
    print_asset_link(
        "Vector Search endpoint",
        vector_search_endpoint_url(WORKSPACE_HOST, VS_ENDPOINT_NAME, WORKSPACE_ORG_ID),
    )
except Exception:
    print(f"Creating Vector Search endpoint '{VS_ENDPOINT_NAME}'...")
    w.vector_search_endpoints.create_endpoint_and_wait(
        name=VS_ENDPOINT_NAME,
        endpoint_type=EndpointType.STANDARD,
    )
    print(f"Vector Search endpoint '{VS_ENDPOINT_NAME}' is ONLINE.")
    print_asset_link(
        "Vector Search endpoint",
        vector_search_endpoint_url(WORKSPACE_HOST, VS_ENDPOINT_NAME, WORKSPACE_ORG_ID),
    )

# Wait until endpoint is ONLINE
for attempt in range(60):
    endpoint = w.vector_search_endpoints.get_endpoint(VS_ENDPOINT_NAME)
    status = endpoint.endpoint_status.state.value
    if status == "ONLINE":
        break
    if attempt % 6 == 0:
        print(f"  Waiting for endpoint to be ONLINE (currently: {status})...")
    time.sleep(10)
else:
    print(f"WARNING: Endpoint status is '{status}' after 10 minutes. It may still be provisioning.")

print(f"Endpoint '{VS_ENDPOINT_NAME}' is ready.")

# COMMAND ----------

spark.sql(f"""
ALTER TABLE {FULL_SCHEMA}.{workshop.chunk_table_name}
  SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

client = VectorSearchClient()

# Delete the existing index if it exists
try:
    client.delete_index(
        endpoint_name=VS_ENDPOINT_NAME,
        index_name=VS_INDEX_NAME,
        # force=True
    )
    print(f"Deleted existing index: {VS_INDEX_NAME}")
except Exception as e:
    print(f"No existing index to delete or error occurred: {e}")

# Create a new index
index = client.create_delta_sync_index(
    endpoint_name=VS_ENDPOINT_NAME,
    source_table_name=f"{FULL_SCHEMA}.{workshop.chunk_table_name}",
    index_name=VS_INDEX_NAME,
    pipeline_type="TRIGGERED",
    primary_key="chunk_id",
    embedding_source_column="content",
    embedding_model_endpoint_name="databricks-gte-large-en",
)

print(f"Vector Search index '{VS_INDEX_NAME}' created.")
_index_url = vector_search_index_url_from_api(w, VS_INDEX_NAME)
if not _index_url:
    _index_url = vector_search_index_catalog_url(WORKSPACE_HOST, VS_INDEX_NAME)
print_asset_link("Vector Search index", _index_url)

# COMMAND ----------

# MAGIC %md
# MAGIC    
# MAGIC ## Step 5: Create Genie Space
# MAGIC
# MAGIC Genie lets you ask questions about your data in plain English. It converts your questions into SQL automatically.
# MAGIC
# MAGIC This creates a Genie Space connected to all industry data tables.

# COMMAND ----------

import json

from lib.workspace_links import genie_space_url, print_asset_link

GENIE_SPACE_TITLE = workshop.genie_title
genie_space_id = None

# Get the first available SQL warehouse
warehouses = w.warehouses.list()
warehouse_id = None
for wh in warehouses:
    if wh.state and wh.state.value in ("RUNNING", "STARTING"):
        warehouse_id = wh.id
        break
    if wh.id:
        warehouse_id = wh.id  # fallback to any warehouse

if not warehouse_id:
    print("WARNING: No SQL warehouse found. Please create one and re-run this cell.")
else:
    table_identifiers = [f"{FULL_SCHEMA}.{t}" for t in tables]

    # Check if a Genie Space with this title already exists
    existing_spaces = w.api_client.do("GET", "/api/2.0/genie/spaces")
    genie_space_id = None
    for space in existing_spaces.get("spaces", []):
        if space.get("title") == GENIE_SPACE_TITLE:
            genie_space_id = space.get("space_id")
            print(f"Genie Space '{GENIE_SPACE_TITLE}' already exists (ID: {genie_space_id})")
            print_asset_link("Genie Space", genie_space_url(WORKSPACE_HOST, genie_space_id, WORKSPACE_ORG_ID))
            break

    if not genie_space_id:
        print(f"Creating Genie Space '{GENIE_SPACE_TITLE}'...")
        serialized = json.dumps({
            "version": 2,
            "data_sources": {
                "tables": [{"identifier": t} for t in sorted(table_identifiers)]
            }
        })
        response = w.api_client.do("POST", "/api/2.0/genie/spaces", body={
            "title": GENIE_SPACE_TITLE,
            "description": workshop.genie_description,
            "warehouse_id": warehouse_id,
            "serialized_space": serialized,
        })
        genie_space_id = response.get("space_id")
        print(f"Genie Space created (ID: {genie_space_id})")
        print_asset_link("Genie Space", genie_space_url(WORKSPACE_HOST, genie_space_id, WORKSPACE_ORG_ID))

# COMMAND ----------

# MAGIC %md
# MAGIC    
# MAGIC ## Step 6: Create MLflow Experiment
# MAGIC
# MAGIC MLflow tracks your agent's performance. This creates an experiment where traces and evaluation metrics will be logged.

# COMMAND ----------

import mlflow

from lib.workspace_links import mlflow_experiment_url, print_asset_link

mlflow.set_tracking_uri("databricks")

username = spark.sql("SELECT current_user()").collect()[0][0]
experiment_name = f"/Users/{username}/{workshop.mlflow_experiment_suffix}"

try:
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment and experiment.lifecycle_stage == "active":
        experiment_id = experiment.experiment_id
        print(f"MLflow experiment already exists: {experiment_name} (ID: {experiment_id})")
    else:
        experiment_id = mlflow.create_experiment(experiment_name)
        print(f"MLflow experiment created: {experiment_name} (ID: {experiment_id})")
except Exception:
    experiment_id = mlflow.create_experiment(experiment_name)
    print(f"MLflow experiment created: {experiment_name} (ID: {experiment_id})")

print_asset_link("MLflow experiment", mlflow_experiment_url(WORKSPACE_HOST, experiment_id))

# COMMAND ----------

from lib.workspace_links import uc_function_url

if workshop.optional_udf_sql:
    print("UC function SQL definition:")
    print(workshop.optional_udf_sql.strip())
    print()
    spark.sql(workshop.optional_udf_sql)
    udf_full_name = f"{FULL_SCHEMA}.{workshop.optional_udf_name}"
    print(f"Registered UC function: {udf_full_name}")
    print_asset_link(
        "UC function",
        uc_function_url(WORKSPACE_HOST, FULL_SCHEMA, workshop.optional_udf_name),
    )
else:
    print("No optional UC function for this industry.")

# COMMAND ----------

# MAGIC %md
# MAGIC    
# MAGIC ## Setup Complete
# MAGIC
# MAGIC All resources have been created. Here's a summary of everything that's ready for you:

# COMMAND ----------

print("=" * 70)
print(f"  {workshop.brand_name.upper()} WORKSHOP SETUP COMPLETE")
print("=" * 70)
print()
print(f"  Catalog/Schema:     {FULL_SCHEMA}")
print()
print("  Data Tables:")
for table in tables:
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_SCHEMA}.{table}").collect()[0]["cnt"]
    print(f"    {table:25s} {count:>8,} rows")
chunks_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_SCHEMA}.{workshop.chunk_table_name}").collect()[0]["cnt"]
print(f"    {workshop.chunk_table_name:25s} {chunks_count:>8,} chunks")
print()
print(f"  Vector Search Endpoint:  {VS_ENDPOINT_NAME}")
print(f"  Vector Search Index:     {VS_INDEX_NAME}")
print()
print("  Validation links:")
print_asset_link(
    "Vector Search endpoint",
    vector_search_endpoint_url(WORKSPACE_HOST, VS_ENDPOINT_NAME, WORKSPACE_ORG_ID),
)
_index_summary_url = vector_search_index_url_from_api(w, VS_INDEX_NAME)
if not _index_summary_url:
    _index_summary_url = vector_search_index_catalog_url(WORKSPACE_HOST, VS_INDEX_NAME)
print_asset_link("Vector Search index", _index_summary_url)
if genie_space_id:
    print(f"  Genie Space ID:          {genie_space_id}")
    print(f"  Genie Space Title:       {GENIE_SPACE_TITLE}")
    print_asset_link("Genie Space", genie_space_url(WORKSPACE_HOST, genie_space_id, WORKSPACE_ORG_ID))
print()
print(f"  MLflow Experiment:       {experiment_name}")
print(f"  MLflow Experiment ID:    {experiment_id}")
print_asset_link("MLflow experiment", mlflow_experiment_url(WORKSPACE_HOST, experiment_id))
if workshop.optional_udf_name:
    print_asset_link(
        "UC function",
        uc_function_url(WORKSPACE_HOST, FULL_SCHEMA, workshop.optional_udf_name),
    )
print()
print("=" * 70)
print("  Next Steps:")
print("    1. Open the Genie Space and try asking questions about your data")
print("    2. Explore the Vector Search index in Catalog Explorer")
print("    3. Open the Databricks Playground to build your first agent")
print("    4. See the README for detailed workshop modules")
print("=" * 70)

# COMMAND ----------

# import mlflow 
# mlflow.create_experiment(
#     name="/Users/<your email>/<experiment name>",
#     artifact_location="dbfs:/Volumes/<catalog>/<schema>/<volume>/mlflow-artifacts"
# )

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Playground Industry System Prompt
# MAGIC
# MAGIC Use this system prompt for the eventual agent in the playground.

# COMMAND ----------

from verticals.registry import get_system_prompt
system_prompt = get_system_prompt(INDUSTRY)


print("=" * 70)
print(f"  SYSTEM PROMPT: \n\n {system_prompt}")
print("=" * 70)

# COMMAND ----------


