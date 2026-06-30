# Workshop Data Setup

> **This is the first step for all workshop levels.** Complete this setup before starting any workshop (Simple, Medium, or Advanced).

This creates the shared dataset that every workshop level depends on: industry data tables, chunked documents, a Vector Search index, a Genie Space, and an MLflow experiment — all in a Unity Catalog schema you choose.

You pick **one industry** to set up:

| Industry | Brand | Data tables | Documents |
|----------|-------|-------------|-----------|
| `education` (default) | EduPath Academy | `customers`, `products`, `stores`, `transactions`, `transaction_items`, `payment_history` (school semantics) | course/policy docs |
| `retail` | FreshMart | Same six tables (grocery semantics) | store policy docs |
| `financial_services` | Meridian Capital Partners | `clients`, `accounts`, `trades`, `portfolio_holdings`, `dailyprice`, `company_profile` | market-shock news articles |

---

## Before you start

Both setup paths write data through a **SQL warehouse**, so you need:

- A **running SQL warehouse** (Compute → SQL Warehouses in Databricks)
- **Unity Catalog** access — permission to create a catalog/schema and tables
- A workspace with **Vector Search** and the **Foundation Model API** enabled

---

## Choose Your Path

| Path | Best for | Time |
|------|----------|------|
| **[Path A: Local CLI](#path-a-local-cli)** | Running setup from your laptop | ~15 min |
| **[Path B: Workspace Notebook](#path-b-workspace-notebook)** | Everything inside Databricks, no local tools | ~15 min |

Both paths run the **same code** and produce the **same result**. Pick one.

---

## Path A: Local CLI

Run one command from your laptop. It connects to your Databricks workspace via the CLI.

### Prerequisites

| Tool | Install |
|------|---------|
| Databricks CLI | `brew tap databricks/tap && brew install databricks` |
| Python 3.9+ | [python.org](https://www.python.org/downloads/) |

### Step 0: Clone the repository

```bash
git clone https://github.com/AnanyaDBJ/databricks-ai-workshops.git
cd databricks-ai-workshops
```

### Step 1: Authenticate

```bash
databricks auth login --profile DEFAULT
```

Follow the browser prompts, then verify:

```bash
databricks current-user me --profile DEFAULT
```

### Step 2: Find your warehouse ID

```bash
databricks warehouses list --profile DEFAULT
```

Pick a warehouse that shows `RUNNING` and copy its ID.

### Step 3: Install dependencies

```bash
cd data
pip install -r requirements.txt
```

### Step 4: Run setup (one command)

```bash
python local_cli_setup_script/setup.py \
  --industry retail \
  --catalog <CATALOG> \
  --schema <SCHEMA> \
  --profile DEFAULT \
  --warehouse-id <WAREHOUSE-ID>
```

Replace `<CATALOG>` and `<SCHEMA>` with names you choose (e.g. `my_catalog` and `retail_agent`), and `<WAREHOUSE-ID>` with the ID from Step 2. Swap `--industry` for `education` or `financial_services` if you prefer.

This creates the catalog and schema, then all six setup steps: data tables, chunked documents, the Vector Search endpoint + index, a Genie Space, and an MLflow experiment. The Vector Search step takes 5–10 minutes to provision.

> **Data only?** Add `--skip-vector-search`, `--skip-genie`, and/or `--skip-mlflow` to skip those steps.

When it finishes it prints a summary:

```
======================================================================
  WORKSHOP SETUP COMPLETE
======================================================================
  Catalog/Schema:          my_catalog.retail_agent
  Vector Search index:     my_catalog.retail_agent.policy_docs_index
  Genie Space ID:          01ef...abcd
  MLflow experiment:       /Users/you@co.com/... (ID: 1234567890123456)
======================================================================
```

**Save the Vector Search index, Genie Space ID, and MLflow experiment** — your workshop level asks for them.

### Done!

Go to your workshop level:

| Level | Next step |
|-------|-----------|
| Simple (L100) | [`simple/LAB_GUIDE.md`](../simple/LAB_GUIDE.md) |
| Medium (L200) | [`medium/lab_instructions/SETUP_GUIDE.md`](../medium/lab_instructions/SETUP_GUIDE.md) |
| Advanced (L300) | [`advanced/WORKSHOP_INSTRUCTIONS.md`](../advanced/WORKSHOP_INSTRUCTIONS.md) |

---

## Path B: Workspace Notebook

Run everything inside Databricks — no local tools needed.

### Step 0: Import the repository into your workspace

1. In the left sidebar, click **Workspace** → **Repos** (or "Git Folders")
2. Click **Add** → **Git Folder**
3. Paste the URL: `https://github.com/AnanyaDBJ/databricks-ai-workshops.git`
4. Click **Create Git Folder**

### Step 1: Open the notebook

Navigate to `data/workspace_setup_script/01_quickstart_setup.py` and open it.

### Step 2: Configure and run

1. At the top, set the **Industry**, **Catalog**, and **Schema** widgets.
2. (Optional) Set the **SQL Warehouse ID** widget to pin a specific warehouse — otherwise one is auto-discovered.
3. Click **Run All** and wait ~10–15 minutes (most of the time is Vector Search provisioning).

> The notebook writes data through a SQL warehouse (not Spark), so make sure one is running.

### Step 3: Copy the output values

When complete, the notebook prints a summary:

```
======================================================================
  WORKSHOP SETUP COMPLETE
======================================================================
  Catalog/Schema:        my_catalog.retail_agent
  Vector Search Index:   my_catalog.retail_agent.policy_docs_index
  Genie Space ID:        01ef...abcd
  MLflow Experiment ID:  1234567890123456
======================================================================
```

**Save these values** — your workshop level asks for them.

### Done!

Go to your workshop level:

| Level | Next step |
|-------|-----------|
| Simple (L100) | [`simple/LAB_GUIDE.md`](../simple/LAB_GUIDE.md) |
| Medium (L200) | [`medium/lab_instructions/SETUP_GUIDE_WORKSPACE_ONLY.md`](../medium/lab_instructions/SETUP_GUIDE_WORKSPACE_ONLY.md) |
| Advanced (L300) | [`advanced/WORKSHOP_INSTRUCTIONS.md`](../advanced/WORKSHOP_INSTRUCTIONS.md) |

---

## What You Now Have

Every industry produces the same kinds of resources in `{catalog}.{schema}`:

| Resource | Description |
|----------|-------------|
| Data tables | Six industry tables (see the table at the top) |
| Document chunk table | Source documents split into searchable chunks |
| Vector Search index | Semantic search over the documents |
| Genie Space | Natural-language querying of your data tables |
| MLflow experiment | Agent tracing and evaluation |

For example, `retail` creates ~200 customers, ~500 products, 10 stores, 2,000 transactions, ~10,000 transaction line items, and 400 payment records, plus the chunked store-policy docs and a `policy_docs_index`. `financial_services` instead loads clients, accounts, a trade ledger, portfolio holdings, and bundled market data (`dailyprice`, `company_profile`), with a `market_news_index` over historical market-shock articles.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `JSONDecodeError` or auth errors | Auth expired — run `databricks auth login --profile DEFAULT` again |
| No SQL warehouse found / `WAREHOUSE_NOT_FOUND` | Start a SQL warehouse (Compute → SQL Warehouses), then re-run. In the notebook you can also set the **SQL Warehouse ID** widget |
| Vector Search step times out | The endpoint can take 10+ minutes — re-run, setup is idempotent |
| Vector Search index shows "Syncing" | Normal — wait 5–10 minutes after creation for the initial sync |
| Notebook widget doesn't list catalogs | Ensure your workspace/cluster has Unity Catalog access |
| Want to start over | Re-run setup — tables are recreated and resources are reused/refreshed |

---

Both paths are idempotent and use a fixed random seed, so re-running produces the same dataset.
