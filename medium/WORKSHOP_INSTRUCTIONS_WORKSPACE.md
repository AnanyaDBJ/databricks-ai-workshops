# Build an AI Agent with Memory — Workspace Only (L200)

This is the same workshop as the [local guide](./WORKSHOP_INSTRUCTIONS.md), but done
**entirely inside Databricks** — no setup on your laptop. You'll build and deploy a
**chatbot that answers questions about your data**: it searches documents, queries tables in
plain English, and remembers what you told it. You run the setup scripts from the in-browser
**Web Terminal**.

The scripts ask you one question at a time and handle the fiddly parts. The parts you learn
from — choosing the agent's tools and writing its instructions — stay in your hands.

## What these words mean

| Term | What it is |
|------|-----------|
| **AI agent** | A chatbot that can *use tools* (search, query data) to answer, not just chat |
| **Tool** | Something the agent can call to get information — here, document search and data queries |
| **Genie** | Ask questions about your tables in plain English; Databricks writes the SQL |
| **Vector Search** | Search documents by *meaning*, not keywords — how the agent looks things up |
| **Lakebase** | A Postgres database that stores the agent's memory (and the chat history) |
| **MLflow experiment** | Where the agent's runs and traces get logged, so you can inspect them |
| **Databricks App** | Where your app runs once deployed — a hosted web app inside Databricks |
| **Service principal** | The app's own login. When deployed, the app acts as this identity, so it needs permission to reach your data |
| **Web Terminal** | A terminal in your browser, inside Databricks — where you run the commands below |

## Before you start

Confirm your workspace has these enabled (ask your admin if unsure):

- **Unity Catalog** — governs access to your data
- **Databricks Apps** — hosts the chat app
- **Lakebase** — the managed database for the agent's memory + chat history
- **Web Terminal** — Settings → Developer → Web Terminal
- A **running SQL warehouse** — needed to create the data tables (Compute → SQL Warehouses)

---

## The short version

Eight steps (one more than the local guide, just for importing the repo and opening the terminal). If a step fails, every one has a by-hand fallback in **[`MANUAL_SETUP.md`](./MANUAL_SETUP.md)**.

1. Import the code into your workspace
2. Set up the data
3. Open the Web Terminal
4. **Set up** — create the database and experiment, write the config
5. **Configure the agent** — pick its tools, give it instructions
6. **Deploy it**
7. **Grant permissions** so the app can reach your data
8. **Verify** it works

Prefer one command that walks steps 4–7? `uv run setup` runs them in order and pauses for you to approve each.

---

## Step 1: Import the code

1. Left sidebar → **Workspace** → **Repos** (may show as "Git Folders")
2. **Add** → **Git Folder**
3. Paste: `https://github.com/AnanyaDBJ/databricks-ai-workshops.git`
4. **Create Git Folder**

Your code lands at `/Workspace/Repos/<your-username>/databricks-ai-workshops/`.

---

## Step 2: Set up the data

**What this does:** creates the tables, documents, Genie space, and search index your agent will use.

Follow **Path B (Workspace Notebook)** in [`data/README.md`](../data/README.md#path-b-workspace-notebook):

1. Open `data/workspace_setup_script/01_quickstart_setup.py`
2. Set the **catalog** and **schema** in the dropdowns at the top
3. Click **Run All** (~10–15 minutes)

Note these values from the output — the scripts will ask for them:

| Value | Looks like |
|------|---------|
| MLflow experiment ID | `1234567890123456` |
| Vector Search index | `my_catalog.my_schema.policy_docs_index` |
| Genie space ID | `01abcdef12345678` |
| Catalog and schema | `my_catalog.my_schema` |

---

## Step 3: Open the Web Terminal

1. Click the `>_` icon in the bottom panel (or Settings → Developer → Web Terminal).
2. Go to the project folder:
   ```bash
   cd /Workspace/Repos/<your-username>/databricks-ai-workshops/medium
   ```
3. Make sure `uv` is available (skip if `uv --version` already works):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.local/bin/env
   ```

> **No `uv`?** Use `pip install -e .` (Python 3.12), then the plain command names (`quickstart`, `configure-agent`…) instead of `uv run …`. Details: [`MANUAL_SETUP.md` → Running without uv](./MANUAL_SETUP.md#running-without-uv). Or skip the scripts entirely and follow [`MANUAL_SETUP.md`](./MANUAL_SETUP.md) through the UI.

---

## Step 4: Set up

**What this does:** creates the agent's memory database and the MLflow experiment, and fills in all the config files — so you never hand-edit them.

```bash
uv run quickstart
```

It asks you, one at a time (each has a default — press **Enter** to accept, or type your own): the **model**, an **experiment name**, a **Lakebase database name** (it creates one — no UI), and an **app name**. Then it writes `.env` and fills `databricks.yml` completely — including your workspace address.

> Reusing an existing Lakebase database? Add `--lakebase-provisioned-name <name>`.
>
> If this step fails → [`MANUAL_SETUP.md` → Lakebase & config](./MANUAL_SETUP.md#lakebase--config-quickstart).

---

## Step 5: Configure the agent

**What this does:** you decide what your agent can *do*. The script lists the document search indexes and Genie spaces in your workspace; you pick the ones you want and it wires them in. You also give the agent a **name** and a **system prompt** (its instructions).

```bash
uv run configure-agent
```

Pick your tools from the numbered list, write a short system prompt (for example: *"You are a helpful assistant for a retail store. Use the tools to answer questions about policies and sales data."*), and you're done. **Re-run it anytime** to change your choices. To browse what's available first: `uv run discover-tools`.

> If this step fails → [`MANUAL_SETUP.md` → Configure the agent](./MANUAL_SETUP.md#configure-the-agent-configure-agent).

<details>
<summary><b>Optional — non-interactive, and routing through AI Gateway</b></summary>

Pass everything as flags instead of prompts:

```bash
uv run configure-agent \
  --name retail-agent \
  --system-prompt "You are a retail store operations assistant." \
  --vector-index my_catalog.my_schema.policy_docs_index \
  --genie-space 01abcdef12345678
```

**AI Gateway** is a governed front door for models (rate limits, usage tracking, guardrails). To route through it, two settings must agree — `AGENT_USE_AI_GATEWAY=true` **and** `AGENT_MODEL` set to a gateway endpoint (not a plain serving-endpoint name). Setting one without the other only fails when you send a message. The local guide's AI Gateway box has the full table.

```bash
uv run configure-agent --use-ai-gateway true --model <catalog>.<schema>.<gateway-endpoint>
```
</details>

---

## Step 6: Deploy the app

**What this does:** uploads your code and turns it into a live, hosted web app. Step 4 already filled in the config, so there's nothing to edit.

```bash
databricks bundle validate
databricks bundle deploy
# Workspace-only cleanup: remove large build files before the app is packaged (see note)
rm -rf .databricks/bundle/dev/bin .databricks/bundle/dev/terraform/.terraform
databricks bundle run agent_openai_agents_sdk
```

The first start takes **3–5 minutes** (the app installs dependencies and builds the website on first boot).

> **Why the `rm`?** `deploy` downloads large tool binaries into the same folder that gets packaged as the app's source, which has a 50MB size limit — remove them or packaging fails. More: [`MANUAL_SETUP.md` → Deploy](./MANUAL_SETUP.md#deploy).

---

## Step 7: Grant permissions

**What this does:** the deployed app runs as its own identity (a *service principal*), separate from you. It needs permission to reach the things it uses. This one command grants all of them.

```bash
uv run grant-all
```

It finds the app's identity automatically and grants access to its **memory database** (without this the app crashes on startup, because you own those tables from setup), **your data** in Unity Catalog, the **Genie space**, and the **AI Gateway endpoint** (only if you turned that on).

If a grant can't be done automatically (Genie and the gateway sometimes can't via the API), the command prints the exact UI click — Genie space → **Share**, or Serving endpoint → **Permissions**.

> If this step fails → [`MANUAL_SETUP.md` → Grant permissions](./MANUAL_SETUP.md#grant-permissions-grant-all).

---

## Step 8: Verify it works

1. **Compute → Apps** → your app. The status dot should turn green (**Running**). If it says **Starting**, wait; if **Crashed**, see below.
2. App → **Logs** — you want to see `Uvicorn running on http://0.0.0.0:8000` and `Server is running on http://localhost:3000`.
3. Click the **app URL** and try:

| Try asking | What it exercises |
|--------|---------------|
| "What is the refund policy?" | Document search |
| "How many customers do we have?" | Genie (data query) |
| "Remember my name is Alice" | Memory (save) |
| "What's my name?" (after refresh) | Memory (recall) |

If it answers with real, tool-grounded responses, you're done. 🎉

---

## If something goes wrong

Every setup script is safe to re-run. Start there; if it still fails, do that step by hand from **[`MANUAL_SETUP.md`](./MANUAL_SETUP.md)**.

**Setup**
| What you see | What it means → fix |
|---|---|
| `uv: command not found` | Run the `uv` install line in Step 3, or follow `MANUAL_SETUP.md` (no scripts needed). |
| `configure-agent` finds no tools | The data setup (Step 2) didn't run in this workspace, or you're pointed elsewhere. Re-check; or pass `--vector-index`/`--genie-space` directly. |

**Deploy**
| What you see | What it means → fix |
|---|---|
| `Failed to snapshot source code... larger than maximum allowed file size` | The build binaries weren't removed. Run the `rm -rf .databricks/...` line, then `databricks bundle run` again. |
| `workspace_id mismatch` | The workspace was recreated with a new ID. [Clear the stale one in 3 places.](./MANUAL_SETUP.md#workspace_id-mismatch-provider-is-configured-for-workspace-x-but-got-y) |

**Permissions / runtime**
| What you see | What it means → fix |
|---|---|
| App shows **Crashed** | Open App → **Logs** and scroll to the error (often a permission issue below, or a typo in `databricks.yml`). |
| `permission denied for schema` | The app can't use its database yet. Run `uv run grant-all`, or [drop the schemas and let the app recreate them](./MANUAL_SETUP.md#app-crashes-with-permission-denied-for-schema-public--drizzle--ai_chatbot). |
| `relation "ai_chatbot"."Chat" already exists` | Leftover tables. `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` then restart. |
| `Lakebase unavailable` | The database details in `databricks.yml` don't match your instance. Re-run `uv run quickstart`, or fix per `MANUAL_SETUP.md`. |
| Agent ignores its tools | The tools aren't wired in. Re-run `uv run configure-agent`. |
