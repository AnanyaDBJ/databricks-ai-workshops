# Workshop: Deploy AI Agent with Memory (Workspace Only)

Deploy the L200 AI agent app **entirely from within a Databricks workspace** — no local machine setup. You run the same setup scripts as the local guide, from the in-browser **Web Terminal**.

The scripts are input-driven: you provide your resources one prompt at a time and they handle creation, config edits, and grants. You still choose your tools and write the agent's instructions.

> **If a script fails** (workspaces differ — this happens), every step has a by-hand equivalent in **[`MANUAL_SETUP.md`](./MANUAL_SETUP.md)**. Each automated step links to its manual fallback.

---

## Prerequisites

Confirm your workspace has these enabled (ask your admin if unsure):

- **Unity Catalog** — data tables and permissions
- **Databricks Apps** — hosts the chat application
- **Lakebase** — managed PostgreSQL (agent memory + chat history)
- **Web Terminal** — in-browser terminal (Settings > Developer > Web Terminal)
- A **running SQL warehouse** — needed to create data tables (Compute > SQL Warehouses)

---

## Step 1: Import the Repository into Your Workspace

1. Left sidebar → **Workspace** > **Repos** (may appear as "Git Folders")
2. **Add** > **Git Folder**
3. Paste: `https://github.com/AnanyaDBJ/databricks-ai-workshops.git`
4. **Create Git Folder**

Your code lands at `/Workspace/Repos/<your-username>/databricks-ai-workshops/`.

---

## Step 2: Set Up Your Data

Complete **Path B (Workspace Notebook)** from [`data/README.md`](../data/README.md#path-b-workspace-notebook).

1. Open `data/workspace_setup_script/01_quickstart_setup.py`
2. Select your **catalog** and **schema** in the dropdown widgets
3. **Run All** (~10–15 minutes)

Note these values from the output — you'll paste them when the scripts prompt (or use them in the manual fallback):

| Value | Looks like |
|------|---------|
| MLflow Experiment ID | `1234567890123456` |
| Vector Search Index name | `my_catalog.my_schema.policy_docs_index` |
| Genie Space ID | `01abcdef12345678` |
| Catalog.Schema | `my_catalog.my_schema` |

---

## Step 3: Open the Web Terminal

1. Open the Web Terminal: the `>_` icon in the bottom panel, or Settings > Developer > Web Terminal.
2. Move into the project:
   ```bash
   cd /Workspace/Repos/<your-username>/databricks-ai-workshops/medium
   ```
3. Ensure `uv` is available (skip if `uv --version` already works):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.local/bin/env
   ```
   > **No `uv`?** Use plain pip instead — `pip install -e .` (Python 3.12), then run the bare command names (`quickstart`, `configure-agent`, `grant-all`, `start-app`) wherever this guide says `uv run …`. Full steps: [`MANUAL_SETUP.md` → Running without uv](./MANUAL_SETUP.md#running-without-uv).

> Prefer not to use scripts at all? Follow **[`MANUAL_SETUP.md`](./MANUAL_SETUP.md)** end to end instead — it covers every step through the UI, SQL Editor, and file editor.

---

## Step 4: Quickstart — Lakebase, experiment, config

```bash
uv run quickstart
```

From your prompted input this creates the **Lakebase** instance (autoscaling project + branch — no UI needed), sets up the **MLflow experiment**, writes `.env`, and fills in `databricks.yml` **completely** — app name, **workspace host**, experiment, and Lakebase resources — so you never hand-edit it before deploy. It **prompts for the experiment name, the Lakebase project name, and the app name**, each prepopulated with a default — press **Enter** to accept, or type your own to override.

Using a **provisioned** Lakebase instance instead? Pass its name so nothing is created:

```bash
uv run quickstart --lakebase-provisioned-name my-agent-workshop
```

> **Fallback:** [`MANUAL_SETUP.md` → Lakebase & config](./MANUAL_SETUP.md#lakebase--config-quickstart) — create the instance in the UI (Compute > Lakebase), read its connection details, and edit `databricks.yml` by hand (including the provisioned-instance variant).

---

## Step 5: Configure the agent — pick your tools

```bash
uv run configure-agent
```

Lists your Vector Search indexes and Genie spaces, lets you pick by number, then writes `agent_server/agent.py` — building the correct `/api/2.0/mcp/...` URLs (dots → slashes) and setting `MCP_SERVERS`. It also asks for the agent **name** and **system prompt**, and writes your model choice to `.env`.

**You choose the tools and write the prompt; the script handles the URLs.** Re-run any time.

Non-interactive equivalent:

```bash
uv run configure-agent \
  --name retail-agent \
  --system-prompt "You are a retail store operations assistant." \
  --vector-index my_catalog.my_schema.policy_docs_index \
  --genie-space 01abcdef12345678
```

For the AI Gateway governance exercise, route through the gateway (both settings are coupled — see the local guide's model table):

```bash
uv run configure-agent --use-ai-gateway true --model <catalog>.<schema>.<gateway-endpoint>
```

> **Fallback:** [`MANUAL_SETUP.md` → Configure the agent](./MANUAL_SETUP.md#configure-the-agent-configure-agent) — edit the `# GENERATED` block of `agent.py` in the workspace file editor.

---

## Step 6: Deploy the App

Deploy it yourself from the Web Terminal — this is the "ship it" moment:

```bash
databricks bundle validate
databricks bundle deploy
# Required in the workspace: remove large terraform binaries before the app snapshot
rm -rf .databricks/bundle/dev/bin .databricks/bundle/dev/terraform/.terraform
databricks bundle run agent_openai_agents_sdk
```

> **Why the `rm`?** `deploy` downloads terraform binaries (~50MB+) into `.databricks/`, the same directory used as the app source. The source snapshot has a 50MB limit and fails if they're left in. First startup takes **3–5 minutes**.
>
> **Fallback / details:** [`MANUAL_SETUP.md` → Deploy](./MANUAL_SETUP.md#deploy).

---

## Step 7: Grant Permissions

```bash
uv run grant-all
```

Resolves the app's service principal automatically and grants everything it needs — **Lakebase** `USAGE + CREATE` on `public`/`drizzle`/`ai_chatbot`/`agent_openai_memory` (this is what a bare deploy crashes on, since you own the schemas from local testing), **Unity Catalog** (`USE CATALOG`/`USE SCHEMA`/`SELECT`), **Genie** "Can Run", and **AI Gateway** `CAN_QUERY` (only when `AGENT_USE_AI_GATEWAY=true`). Each grant is independent; a failure in one is reported and the rest still run.

Genie "Can Run" and the gateway grant sometimes can't be set via API in a given workspace — `grant-all` prints the exact object and SP so you can do those in the UI (Genie space → **Share**; Serving endpoint → **Permissions**).

> **Fallback:** [`MANUAL_SETUP.md` → Grant permissions](./MANUAL_SETUP.md#grant-permissions-grant-all) — the SP-id lookup, the UC SQL to run in the SQL Editor, and the Genie share steps.

---

## Step 8: Verify the Deployment

1. **Compute** > **Apps** → your app; the status dot should turn green (**Running**). **Starting** → wait; **Crashed** → see Troubleshooting.
2. App > **Logs** tab — look for `Uvicorn running on http://0.0.0.0:8000` and `Server is running on http://localhost:3000`.
3. Click the **app URL** and try:

| Prompt | What it tests |
|--------|---------------|
| "What is the refund policy?" | Vector Search (document retrieval) |
| "How many customers do we have?" | Genie Space (data queries) |
| "Remember my name is Alice" | Agent memory (store) |
| "What's my name?" (after refresh) | Agent memory (recall) |

---

## Troubleshooting

| What you see | How to fix it |
|---|---|
| A setup script fails partway | Re-run it (all idempotent), or do that step by hand from [`MANUAL_SETUP.md`](./MANUAL_SETUP.md) |
| `uv: command not found` in Web Terminal | Run the `uv` install line in Step 3, or follow `MANUAL_SETUP.md` (no scripts needed) |
| `configure-agent` finds no tools | Confirm Step 2 ran in this workspace; or pass `--vector-index`/`--genie-space` directly |
| `grant-all` can't resolve the SP | Deploy the app first, or pass `--sp-client-id`; see `MANUAL_SETUP.md` → Grant permissions |
| `relation "ai_chatbot"."Chat" already exists` | Drop schemas: `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` then restart app |
| `permission denied for schema` | Run `uv run grant-all`, or drop schemas and let the app recreate them |
| App shows **Crashed** | App > Logs tab > scroll to the error (often a `databricks.yml` typo) |
| `Lakebase unavailable` | `branch:`/`database:` in `databricks.yml` don't match your instance — re-run `uv run quickstart` or fix per `MANUAL_SETUP.md` |
| Agent doesn't use tools | Re-run `uv run configure-agent`; URLs must be `/api/2.0/mcp/vector-search/catalog/schema/index` |
| `Failed to snapshot source code... larger than maximum allowed file size` | Terraform binaries not removed — run the `rm -rf .databricks/...` line, then re-run `databricks bundle run` |
| `workspace_id mismatch` on deploy | Workspace recreated with a new id; clear the stale id in 3 places — see [`MANUAL_SETUP.md`](./MANUAL_SETUP.md#workspace_id-mismatch-provider-is-configured-for-workspace-x-but-got-y) |
| App crashes: `permission denied for schema` (public/drizzle/ai_chatbot) | Run `uv run grant-all`, or drop those schemas and let the SP recreate them — see [`MANUAL_SETUP.md`](./MANUAL_SETUP.md#app-crashes-with-permission-denied-for-schema-public--drizzle--ai_chatbot) |
