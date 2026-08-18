# Workshop Data Setup

> **This is the first step for all workshop levels.** Complete this setup before starting any workshop (Simple, Medium, or Advanced).

This gives your agent something to work with. In one run it creates, in a location you choose:

- **Sample tables** — realistic business data (customers, products, transactions, …) for the agent to query
- **Documents, made searchable** — policy/course docs split into chunks and indexed so the agent can search them by meaning (a **Vector Search index**)
- **A Genie space** — lets you (and the agent) ask questions about those tables in plain English
- **An MLflow experiment** — a place where the agent's activity gets logged so you can inspect it later

Everything lands in a **catalog and schema** you name (Databricks' way of organizing and governing data). Pick **one industry** — the shape is the same, only the flavor of the data differs:

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

> **Run every command below from the repository root** — the `databricks-ai-workshops/`
> directory you get after cloning. The paths are written `data/...` on purpose so you
> stay in one place; do **not** `cd` into subfolders. (`cd databricks-ai-workshops` after
> the clone and stay there.)

### Prerequisites

| Tool | Install |
|------|---------|
| Databricks CLI | `brew tap databricks/tap && brew install databricks` |
| Python 3.9+ | [python.org](https://www.python.org/downloads/) |

### Step 0: Clone the repository

```bash
git clone https://github.com/AnanyaDBJ/databricks-ai-workshops.git
cd databricks-ai-workshops          # ← the repo root; run every step from here
```

### Step 1: Authenticate

Point the CLI at the **specific workspace** you want to set up. Teams often stand up a dedicated workshop workspace, so don't assume the default — use that workspace's URL:

```bash
databricks auth login --host https://<your-workspace-url> --profile DEFAULT
```

Replace `<your-workspace-url>` with your workspace host (e.g. `dbc-a1b2c3d4-e5f6.cloud.databricks.com` or `adb-1234567890.11.azuredatabricks.net`).

Follow the browser prompts, then verify you're connected to the right workspace:

```bash
databricks current-user me --profile DEFAULT
```

### Step 2: Install dependencies

From the repo root (no `cd`):

```bash
pip install -r data/requirements.txt
```

### Step 3: Run setup (one command)

Still from the repo root — the `data/` prefix is intentional:

```bash
python data/local_cli_setup_script/setup.py \
  --industry retail \
  --catalog <CATALOG> \
  --schema <SCHEMA> \
  --profile DEFAULT
```

> The script figures out its own location, so it reads the workshop documents and data
> correctly no matter what — the only requirement is that **you** run it with the path
> above from the repo root, so your shell can find the file.

Replace `<CATALOG>` and `<SCHEMA>` with names you choose (e.g. `my_catalog` and `retail_agent`). Swap `--industry` for `education` or `financial_services` if you prefer. The first available SQL warehouse is auto-detected (a running one is preferred) — pass `--warehouse-id <id>` only to pin a specific warehouse (find IDs with `databricks warehouses list --profile DEFAULT`).

**You'll be prompted to name each resource.** The script proposes a sensible default for the Vector Search index, Vector Search endpoint, document chunk table, Genie Space, and MLflow experiment — **press Enter to accept each default**, or type your own name to override:

```
=== Resource names (press Enter to accept each default) ===
  Document chunk table name [policy_docs_chunked]:
  Vector Search index name [policy_docs_index]: my_docs_index
  Vector Search endpoint name [retail-vs-retail-agent]:
  Genie Space name [FreshMart Data (retail_agent)]:
  MLflow experiment name [freshmart-agent-workshop]:
```

Prefer to set names up front (or run unattended)? Pass any of these flags to skip that prompt, and add `--non-interactive` to accept all remaining defaults without prompting:

```bash
python data/local_cli_setup_script/setup.py \
  --industry retail --catalog <CATALOG> --schema <SCHEMA> --profile DEFAULT \
  --vs-index-name my_docs_index \
  --vs-endpoint-name my_endpoint \
  --chunk-table-name my_doc_chunks \
  --genie-title "My Store Assistant" \
  --experiment-name my-agent-experiment \
  --non-interactive
```

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
| Medium (L200) | [`medium/WORKSHOP_INSTRUCTIONS.md`](../medium/WORKSHOP_INSTRUCTIONS.md) |
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
2. Optionally set the resource-name widgets — **Vector Search Index/Endpoint Name**, **Document Chunk Table Name**, **Genie Space Name**, **MLflow Experiment Name**. Leave any of these **blank to accept the default** for that resource (same as pressing Enter in the CLI).
3. Click **Run All** and wait ~10–15 minutes (most of the time is Vector Search provisioning). The first available SQL warehouse is auto-detected.

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
| Medium (L200) | [`medium/WORKSHOP_INSTRUCTIONS_WORKSPACE.md`](../medium/WORKSHOP_INSTRUCTIONS_WORKSPACE.md) |
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
| `can't open file '.../setup.py'` / `No such file or directory` | You're in the wrong directory. Run every Path A command from the **repo root** (`databricks-ai-workshops/`) using the `data/...` paths shown — don't `cd` into subfolders |
| `JSONDecodeError` or auth errors | Auth expired — run `databricks auth login --host https://<your-workspace-url> --profile DEFAULT` again |
| No SQL warehouse found / `WAREHOUSE_NOT_FOUND` | Start a SQL warehouse (Compute → SQL Warehouses), then re-run. The CLI also accepts `--warehouse-id <id>` to pin a specific warehouse |
| Vector Search step times out | The endpoint can take 10+ minutes — re-run, setup is idempotent |
| Vector Search index shows "Syncing" | Normal — wait 5–10 minutes after creation for the initial sync |
| Notebook widget doesn't list catalogs | Ensure your workspace/cluster has Unity Catalog access |
| Want to start over | Re-run setup — tables are recreated and resources are reused/refreshed |

---

Both paths are idempotent and use a fixed random seed, so re-running produces the same dataset.
