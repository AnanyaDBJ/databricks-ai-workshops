# Build an AI Agent with Memory on Databricks (L200)

By the end of this workshop you'll have built and deployed a **chatbot that can answer
questions about your data** — it searches documents, queries tables in plain English, and
remembers what you told it earlier in the conversation. You'll run it on your laptop first,
then deploy it as a live web app on Databricks.

You run a few guided scripts that ask you one question at a time and handle the fiddly setup.
The parts you actually learn from — choosing what the agent can do and telling it how to
behave — stay in your hands.

## What these words mean

You'll see these terms throughout. Here's the plain version:

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
| **Unity Catalog** | How Databricks governs who can access which data |

## Before you start

Install these on your machine:

| Tool | Install |
|------|---------|
| Databricks CLI v0.295+ | `brew tap databricks/tap && brew install databricks` |
| uv (Python runner) | [install guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Node.js 20+ | [nodejs.org](https://nodejs.org) |

Your Databricks workspace needs Unity Catalog, Databricks Apps, Lakebase, Vector Search, and the Foundation Model API enabled. Ask your workspace admin if you're unsure.

> **No `uv`?** It's only a local convenience — the deployed app doesn't depend on it. Run `pip install -e .` once (Python 3.12) and use the plain command names (`quickstart`, `configure-agent`…) instead of `uv run …`. Details: [`MANUAL_SETUP.md` → Running without uv](./MANUAL_SETUP.md#running-without-uv).

**Do the data setup first.** It creates the tables, documents, Genie space, and search index your agent will use. Follow **Path A (Local CLI)** in [`data/README.md`](../data/README.md), then keep these values handy — the scripts will ask for them:

- **Catalog and schema** (e.g. `my_catalog.my_schema`)
- **Vector Search index** (e.g. `my_catalog.my_schema.policy_docs_index`)
- **Genie space ID** (e.g. `01abcdef12345678`)
- **MLflow experiment ID** — optional; the setup can make one for you

---

## The short version

The whole workshop is seven steps. If a step ever fails, every one has a by-hand fallback in **[`MANUAL_SETUP.md`](./MANUAL_SETUP.md)**.

1. Get the code
2. **Set up** — log in, create the database and experiment, write the config
3. **Configure the agent** — pick its tools, give it instructions
4. **Run it locally** and chat with it
5. **Deploy it** to Databricks
6. **Grant permissions** so the deployed app can reach your data
7. **Verify** it works live

Prefer one command that walks all of this? `uv run setup` runs the steps in order and pauses for you to approve each. The rest of this guide explains each step so you understand what's happening.

---

## Step 1: Get the code

```bash
git clone https://github.com/AnanyaDBJ/databricks-ai-workshops.git
cd databricks-ai-workshops/medium
```

Run every command from this `medium/` folder.

---

## Step 2: Set up

**What this does:** logs you into Databricks, creates the agent's memory database and the MLflow experiment, and fills in all the config files — so you never hand-edit them.

```bash
uv run quickstart --profile DEFAULT
```

It asks you, one at a time (each has a suggested default — press **Enter** to accept, or type your own):

- **Which model** the agent should use
- **A name for the MLflow experiment**
- **A name for the Lakebase database** (it creates one for you — no clicking through the UI)
- **A name for the app** you'll deploy

Then it writes `.env` (your local settings) and fills `databricks.yml` (the deployment config) completely — login profile, workspace address, experiment, database, and app name.

> Already have a Lakebase database you want to reuse? Add `--lakebase-provisioned-name <name>` (or `--lakebase-autoscaling-endpoint <name>`) and it'll use that instead of creating one.
>
> If this step fails → [`MANUAL_SETUP.md` → Lakebase & config](./MANUAL_SETUP.md#lakebase--config-quickstart).

---

## Step 3: Configure the agent

**What this does:** this is where you decide what your agent can *do*. The script shows you the document search indexes and Genie spaces in your workspace; you pick the ones you want. It then wires them in for you (getting the connection details exactly right is easy to fumble by hand). You also give the agent a **name** and a **system prompt** — the instructions that shape how it answers.

```bash
uv run configure-agent --profile DEFAULT
```

Pick your tools from the numbered list, write a short system prompt (for example: *"You are a helpful assistant for a retail store. Use the tools to answer questions about policies and sales data."*), and you're done. **Re-run it anytime** to change your choices.

Just want to see what's available first? `uv run discover-tools`.

> If this step fails → [`MANUAL_SETUP.md` → Configure the agent](./MANUAL_SETUP.md#configure-the-agent-configure-agent).

<details>
<summary><b>Optional — running it non-interactively</b></summary>

You can pass everything as flags instead of answering prompts:

```bash
uv run configure-agent \
  --name retail-agent \
  --system-prompt "You are a retail store operations assistant." \
  --vector-index my_catalog.my_schema.policy_docs_index \
  --genie-space 01abcdef12345678
```
</details>

<details>
<summary><b>Optional — send model requests through AI Gateway (adds governance)</b></summary>

By default the agent calls the model directly. **AI Gateway** is a governed front door for
models — it adds rate limits, usage tracking, and guardrails. To route through it, two
settings must agree, because they decide *where* requests go and therefore what kind of model
name is valid:

| `AGENT_USE_AI_GATEWAY` | Requests go to | `AGENT_MODEL` must be |
|---|---|---|
| `false` (default) | the model serving endpoints | a serving endpoint name, e.g. `databricks-claude-opus-4-6` |
| `true` | the AI Gateway | a gateway endpoint, e.g. `catalog.schema.my-gateway` |

Setting one without the other is the usual mistake — it only fails when you send a message, not at startup. To use the gateway, set both together:

```bash
uv run configure-agent --use-ai-gateway true --model <catalog>.<schema>.<gateway-endpoint>
```

Ask your instructor for the shared gateway endpoint, or create one under **Serving → AI Gateway**. On startup the server prints which model is active, so you can confirm:
`Agent model: <name> (AI Gateway: True)`.
</details>

---

## Step 4: Run it locally and chat

**What this does:** starts the agent (backend) and the chat website (frontend) on your machine so you can try it before deploying. The database tables are created automatically on first run.

```bash
uv run start-app
```

Open **http://localhost:3000** and try:

- *"What is the return policy for perishable items?"* — uses document search
- *"What are the top 5 products by revenue?"* — uses Genie to query your tables
- *"Remember my name is Alice"*, then refresh the page and ask *"What's my name?"* — uses memory

To confirm the backend is healthy without the UI: `uv run preflight` (starts the server and sends one test message).

> If this step fails → [`MANUAL_SETUP.md` → Run locally](./MANUAL_SETUP.md#run-locally).

---

## Step 5: Deploy to Databricks

**What this does:** uploads your code and turns it into a live, hosted web app. You run this yourself — watching it go out is part of the experience. Step 2 already filled in the deployment config, so there's nothing to edit.

```bash
databricks bundle validate --profile DEFAULT     # check the config
databricks bundle deploy   --profile DEFAULT      # upload code, create the app
databricks bundle run agent_openai_agents_sdk --profile DEFAULT   # start it
```

The first start takes **3–5 minutes** — the app installs its dependencies and builds the website the first time it boots. Every restart pays this cost; that's normal for Databricks Apps.

> Hit a `workspace_id mismatch` error? Your workspace was likely recreated with a new ID — [`MANUAL_SETUP.md` → Troubleshooting deploy](./MANUAL_SETUP.md#workspace_id-mismatch-provider-is-configured-for-workspace-x-but-got-y) has the fix. Other deploy issues (including reusing an existing app) → [`MANUAL_SETUP.md` → Deploy](./MANUAL_SETUP.md#deploy).

---

## Step 6: Grant permissions

**What this does:** the deployed app runs as its own identity (a *service principal*), separate from you. It needs permission to reach the things it uses. This one command grants all of them.

```bash
uv run grant-all --profile DEFAULT
```

It finds the app's identity automatically and grants access to:

- **Its memory database** — so it can read and write the memory and chat-history tables. (Without this, the app crashes on startup, because *you* own those tables from local testing.)
- **Your data** in Unity Catalog — so its tools can read the tables and documents.
- **The Genie space** — so it can answer data questions.
- **The AI Gateway endpoint** — only if you turned that on in Step 3.

Each grant runs independently — if one can't be done automatically, the command tells you the exact click to do it by hand and continues with the rest. If a grant was skipped because a table didn't exist yet (they're created on first use), just run the command again after chatting once.

> If this step fails → [`MANUAL_SETUP.md` → Grant permissions](./MANUAL_SETUP.md#grant-permissions-grant-all).

---

## Step 7: Verify it works

Find your app and open it:

```bash
databricks apps get <your-app-name> --output json --profile DEFAULT | jq '{app_status, compute_status, url}'
```

Open the **url** it prints, and try the same questions from Step 4 (document search, a Genie query, and memory). If it answers with real, tool-grounded responses, you're done. 🎉

To watch what the app is doing: `databricks apps logs <your-app-name> --follow --profile DEFAULT`.

<details>
<summary><b>Optional — test the API directly with curl</b></summary>

```bash
TOKEN=$(databricks auth token --profile DEFAULT | jq -r '.access_token')
APP_URL=$(databricks apps get <your-app-name> --output json --profile DEFAULT | jq -r '.url')

curl -X POST ${APP_URL}/invocations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "Hello, what tools do you have?"}]}'
```
</details>

---

## If something goes wrong

Every setup script is safe to re-run. Start there; if it still fails, do that step by hand from **[`MANUAL_SETUP.md`](./MANUAL_SETUP.md)**.

**Setup**
| What you see | What it means → fix |
|---|---|
| `configure-agent` finds no tools | It's looking in the wrong workspace, or the data setup didn't finish. Check your login profile and that the data setup ran; or pass `--vector-index`/`--genie-space` directly. |
| Vector Search returns no results | The search index is still building. Wait 5–10 minutes after creating it. |

**Deploy**
| What you see | What it means → fix |
|---|---|
| `workspace_id mismatch` | The workspace was recreated with a new ID and a stale one lingers. [Clear it in 3 places.](./MANUAL_SETUP.md#workspace_id-mismatch-provider-is-configured-for-workspace-x-but-got-y) |
| `unknown field` from `bundle deploy` | Your Databricks CLI is old. Upgrade to v0.295.0+. |
| `An app with the same name already exists` | Reuse it: `databricks bundle deployment bind agent_openai_agents_sdk <name> --auto-approve`, or delete it: `databricks apps delete <name>`. |

**Permissions (the app runs, but can't reach something)**
| What you see | What it means → fix |
|---|---|
| App crashes with `permission denied for schema` | The app can't use its database yet. Run `uv run grant-all`, or [drop the schemas and let the app recreate them](./MANUAL_SETUP.md#app-crashes-with-permission-denied-for-schema-public--drizzle--ai_chatbot). |
| `relation "ai_chatbot"."Chat" already exists` | Leftover tables from a previous run. Drop them: `DROP SCHEMA IF EXISTS ai_chatbot CASCADE; DROP SCHEMA IF EXISTS drizzle CASCADE;` then restart. |
| `grant-all` can't find the app's identity | Deploy the app first (Step 5), or pass `--sp-client-id`. |
| Model / endpoint not found | Your model and gateway settings disagree — see Step 3's AI Gateway box. |

**Running**
| What you see | What it means → fix |
|---|---|
| App won't start locally | Something's already using the port. Free it: `lsof -ti :8000 \| xargs kill`. |
| Agent ignores its tools | The tools aren't wired in. Re-run `uv run configure-agent`. |
| Not sure which model it's using | Check the startup log line: `Agent model: <name> (AI Gateway: <bool>)`. |
