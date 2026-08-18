# Workshop: Build an AI Agent with Memory on Databricks

Build and deploy a conversational AI agent with Genie, Vector Search, and persistent memory using the OpenAI Agents SDK.

The setup is script-driven: you provide your resources one prompt at a time and the scripts handle creation, config edits, and permission grants. You still choose your tools and write the agent's instructions — that's the part worth learning.

> **If a script fails in your environment** (this happens — workspaces differ), every step has a by-hand equivalent in **[`MANUAL_SETUP.md`](./MANUAL_SETUP.md)**. Each automated step below links to its manual fallback.

## Prerequisites

| Tool | Install |
|------|---------|
| Databricks CLI v0.295+ | `brew tap databricks/tap && brew install databricks` |
| uv | [install guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Node.js 20+ | [nodejs.org](https://nodejs.org) |

> **No `uv`?** It's only the local runner — deployment uses it on the app's own compute regardless. Run `pip install -e .` once (Python 3.12), then use the bare command names (`quickstart`, `configure-agent`, `grant-all`, `start-app`) wherever this guide says `uv run …`. Full steps: [`MANUAL_SETUP.md` → Running without uv](./MANUAL_SETUP.md#running-without-uv).

Your workspace needs: Unity Catalog, Databricks Apps, Lakebase, Vector Search, and Foundation Model API.

### Data setup (required first)

Complete the data setup before continuing:
**→ [`data/README.md`](../data/README.md) — Path A (Local CLI)**

When done, you should have these values ready to paste when prompted:
- **Catalog.Schema** (e.g., `my_catalog.my_schema`)
- **Vector Search Index** (e.g., `my_catalog.my_schema.policy_docs_index`)
- **Genie Space ID** (e.g., `01abcdef12345678`)
- **MLflow Experiment ID** (e.g., `1234567890123456`) — optional; the setup can create one

---

## Step 1: Clone the Repo

```bash
git clone https://github.com/AnanyaDBJ/databricks-ai-workshops.git
cd databricks-ai-workshops/medium
```

---

## The fast path: `uv run setup`

```bash
uv run setup --profile DEFAULT
```

This guided wizard walks every phase below, pausing so you approve each one and run the deploy yourself. Prefer to understand each piece? Run the phases individually — that's Steps 2–8.

> If any phase errors, the wizard tells you which command to re-run or points you at `MANUAL_SETUP.md`. Phases are independent and re-runnable.

---

## Step 2: Quickstart — auth, experiment, Lakebase, config

```bash
uv run quickstart --profile DEFAULT
```

This interactive wizard handles, from your prompted input:
- Databricks CLI authentication (OAuth login)
- **MLflow experiment** — prompts for the name (prepopulated default; Enter to accept), then creates or reuses it
- **Lakebase instance** — creates an autoscaling project + branch; when creating, prompts for the project name (default provided, Enter to accept). No UI needed.
- **App name** — prompts for it (default `agent-<username>`, Enter to accept)
- Writes `.env` and fills in `databricks.yml` completely — app name, **workspace host**, experiment, and Lakebase resources — so you never hand-edit it before deploy

> Names are prepopulated — press **Enter** to accept a default, or type your own to override. If your `.env` already has an experiment/Lakebase from a previous run, the default is that existing one.

Follow the prompts. Already have a Lakebase instance? Pass it and skip creation:

```bash
uv run quickstart --profile DEFAULT --lakebase-provisioned-name my-db
# or
uv run quickstart --profile DEFAULT --lakebase-autoscaling-endpoint my-endpoint
```

> **Fallback:** [`MANUAL_SETUP.md` → Lakebase & config](./MANUAL_SETUP.md#lakebase--config-quickstart) — create the instance in the UI and fill `.env`/`databricks.yml` by hand.

---

## Step 3: Configure the agent — pick your tools

```bash
uv run configure-agent --profile DEFAULT
```

This lists the Vector Search indexes and Genie spaces in your workspace and lets you select them by number. It then writes `agent_server/agent.py` for you — building the correct `/api/2.0/mcp/...` URLs (converting dots to slashes) and setting `MCP_SERVERS`. It also asks for the agent's **name** and **system prompt**, and writes your model choice to `.env`.

**You choose the tools and write the prompt. The script only removes the copy-paste.** Re-run it any time to change your selections.

Non-interactive (e.g. scripting) equivalent:

```bash
uv run configure-agent \
  --name retail-agent \
  --system-prompt "You are a retail store operations assistant." \
  --vector-index my_catalog.my_schema.policy_docs_index \
  --genie-space 01abcdef12345678
```

To just browse what's available: `uv run discover-tools`.

> **Fallback:** [`MANUAL_SETUP.md` → Configure the agent](./MANUAL_SETUP.md#configure-the-agent-configure-agent) — edit the `# GENERATED` block of `agent.py` by hand.

### Choosing your model (optional)

`configure-agent` prompts for the model and writes it to `.env`; you never edit `agent.py` for this. The defaults work as-is, so you can accept them and revisit for the AI Gateway exercise.

| Variable | Default | What it does |
|---|---|---|
| `AGENT_MODEL` | `databricks-claude-opus-4-6` | Which model the agent calls |
| `AGENT_USE_AI_GATEWAY` | `false` | Route through AI Gateway instead of serving endpoints |

**These two settings are coupled.** The flag decides which base URL the client uses, which decides what kind of name `AGENT_MODEL` has to be:

| `AGENT_USE_AI_GATEWAY` | Requests go to | `AGENT_MODEL` must be |
|---|---|---|
| `false` (default) | `{host}/serving-endpoints` | a serving endpoint name, e.g. `databricks-claude-opus-4-6` |
| `true` | `{host}/ai-gateway/mlflow/v1` | an AI Gateway endpoint, often a UC path like `catalog.schema.my-gw-endpoint` |

Changing one without the other is the most common mistake — a mismatched pair fails at request time, not at startup. To route through AI Gateway (the governance exercise), set both:

```bash
uv run configure-agent --use-ai-gateway true --model <your-catalog>.<your-schema>.<your-gateway-endpoint>
```

Ask your instructor for the shared gateway endpoint, or create your own (**Serving → AI Gateway**). The server logs the resolved pair on startup so you can confirm what's in effect:

```
INFO:agent_server.agent:Agent model: databricks-claude-opus-4-6 (AI Gateway: False)
```

---

## Step 4: Run Locally

```bash
uv run start-app       # backend :8000 + frontend :3000, creates DB tables on first run
uv run preflight       # optional: starts the server and sends one test request
```

Open `http://localhost:3000` and try:
- "What is the return policy for perishable items?" (Vector Search)
- "What are the top 5 products by revenue?" (Genie)
- "Remember my name is Alice" then refresh and ask "What's my name?" (Memory)

> **Fallback:** [`MANUAL_SETUP.md` → Run locally](./MANUAL_SETUP.md#run-locally).

---

## Step 5: Deploy to Databricks Apps

Deploy it yourself — this is the "ship it" moment. `quickstart` already filled `databricks.yml` (host, app name, experiment, Lakebase) and `configure-agent` set the model, so no hand-editing:

```bash
databricks bundle validate --profile DEFAULT
databricks bundle deploy --profile DEFAULT           # uploads code, creates app + resources
databricks bundle run agent_openai_agents_sdk --profile DEFAULT   # starts the app (~3-5 min first time)
```

> First `bundle run` takes a few minutes — the compute installs Python deps and builds the frontend on boot (they aren't shipped). Every restart pays this cost; it's inherent to Apps.
>
> **`workspace_id mismatch` on deploy?** Your workspace was likely recreated with a new id and a stale id lingers — see [`MANUAL_SETUP.md` → Troubleshooting deploy](./MANUAL_SETUP.md#workspace_id-mismatch-provider-is-configured-for-workspace-x-but-got-y).
>
> **Fallback / edits:** [`MANUAL_SETUP.md` → Deploy](./MANUAL_SETUP.md#deploy) — including how to bind an existing app.

---

## Step 6: Grant Permissions

```bash
uv run grant-all --profile DEFAULT
```

This resolves the deployed app's service principal automatically and grants everything it needs, from your own config:
- **Lakebase** schema/table/sequence grants — `USAGE + CREATE` on `public`, `drizzle`, `ai_chatbot`, `agent_openai_memory` (memory + chat history). This is what a bare deploy otherwise crashes on, because you own the schemas from local testing.
- **Unity Catalog** `USE CATALOG` / `USE SCHEMA` / `SELECT` on the catalog.schema your tools read
- **Genie** "Can Run" (or prints the exact UI step if the API can't do it in your workspace)
- **AI Gateway** `CAN_QUERY` on your gateway endpoint — only when `AGENT_USE_AI_GATEWAY=true` (prints the manual step if it can't resolve the endpoint)

Each grant is independent and best-effort — a failure in one is reported and the rest still run. Re-run after the app's first request if any Lakebase table grants were skipped (tables are created on first use).

> **Fallback:** [`MANUAL_SETUP.md` → Grant permissions](./MANUAL_SETUP.md#grant-permissions-grant-all) — the exact SP-id lookup, SQL, and Genie UI steps.

---

## Step 7: Verify the Deployed App

```bash
# Check app status
databricks apps get <your-app-name> --output json --profile DEFAULT | jq '{app_status, compute_status, url}'

# View logs
databricks apps logs <your-app-name> --follow --profile DEFAULT

# Test the endpoint
TOKEN=$(databricks auth token --profile DEFAULT | jq -r '.access_token')
APP_URL=$(databricks apps get <your-app-name> --output json --profile DEFAULT | jq -r '.url')

curl -X POST ${APP_URL}/invocations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "Hello, what tools do you have?"}]}'
```

Open the app URL in your browser to use the chat UI.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| A setup script fails partway | Re-run it (all are idempotent), or do that step by hand from [`MANUAL_SETUP.md`](./MANUAL_SETUP.md) |
| `configure-agent` finds no tools | Confirm the data setup ran and your profile points at the right workspace; or pass `--vector-index`/`--genie-space` directly |
| `grant-all` can't resolve the SP | Deploy the app first, or pass `--sp-client-id`; see `MANUAL_SETUP.md` → Grant permissions |
| `relation "ai_chatbot"."Chat" already exists` | Drop schemas: `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` then restart |
| `relation agent_messages does not exist` | Restart the app — `start_server.py` auto-creates them |
| `permission denied for schema`/`sequence` | Run `uv run grant-all` (or the Step 6 fallback SQL) |
| App crashes after deploy | Check `databricks apps logs` — usually a missing env var or permission |
| `databricks bundle deploy` says "unknown field" | Upgrade CLI to v0.295.0+ |
| `workspace_id mismatch` on deploy | Workspace recreated with a new id; clear the stale id in 3 places — see [`MANUAL_SETUP.md`](./MANUAL_SETUP.md#workspace_id-mismatch-provider-is-configured-for-workspace-x-but-got-y) |
| App crashes: `permission denied for schema` (public/drizzle/ai_chatbot) | Run `uv run grant-all`, or drop those schemas and let the SP recreate them — see [`MANUAL_SETUP.md`](./MANUAL_SETUP.md#app-crashes-with-permission-denied-for-schema-public--drizzle--ai_chatbot) |
| `An app with the same name already exists` | Delete: `databricks apps delete <name>`, or bind: `databricks bundle deployment bind agent_openai_agents_sdk <name> --auto-approve` |
| MCP tools not responding | Re-run `uv run configure-agent`; URLs must match `/api/2.0/mcp/vector-search/catalog/schema/index` |
| Model or endpoint not found | `AGENT_MODEL` and `AGENT_USE_AI_GATEWAY` disagree — see Step 3. Gateway endpoint needs `true`; serving endpoint needs `false` |
| Not sure which model is in use | Check the startup log: `Agent model: <name> (AI Gateway: <bool>)` |
| Vector Search returns no results | Index may not be synced — wait 5–10 min after creation |
| Local app won't start | Check `lsof -ti :8000` — kill orphan processes |
