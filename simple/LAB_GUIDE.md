# L100 Lab Guide: Build Your First AI Agent on Databricks

A complete, step-by-step guide to building, deploying, evaluating, and improving an AI agent using managed Databricks services. Follow this guide at your own pace or as part of an instructor-led workshop.

---

## Overview

In this workshop you will:

1. Set up synthetic data and AI resources for your chosen industry (retail, education, or financial services) in a Databricks workspace
2. Explore AI Gateway for LLM governance
3. Use Genie, Vector Search, and the Playground to prototype an agent
4. Deploy a production agent app with a chat UI
5. Evaluate the agent with MLflow (traces, automated judges, prompt iteration)
6. Provide human-in-the-loop feedback
7. Build managed agents (Knowledge Assistant and Supervisor Agent)

**Total time:** ~3.5 hours self-paced | ~2.5 hours instructor-led

| Section | Topic | Self-Paced | Instructor-Led |
|---------|-------|-----------|----------------|
| 1 | Codebase & Data Setup | 20 min | 15 min |
| 2 | AI Gateway | 15 min | 10 min |
| 3 | Explore Capabilities | 40 min | 30 min |
| 4 | Databricks Apps | 30 min | 20 min |
| 5 | MLflow Evals & Governance | 40 min | 30 min |
| 6 | Human in the Loop | 25 min | 20 min |
| 7 | Managed Agents | 25 min | 20 min |
| 8 | Document Intelligence (Optional) | 15 min | 10 min |

For a summary of what this workshop builds, see the [README](./README.md).

**Pick an industry.** The workshop runs on synthetic data for one of three industry verticals — choose the one closest to your audience and use it throughout:

| Industry | Fictional company | Structured data | Documents |
|----------|------------------|-----------------|-----------|
| `retail` | FreshMart (grocery chain) | Customers, products, stores, transactions | Store policies (returns, loyalty, delivery) |
| `education` | EduPath Academy (higher education) | Students, courses, campuses, enrollments | Academic policies (grading, attendance, refunds) |
| `financial_services` | Meridian Capital Partners (investment firm) | Clients, accounts, simulated trade ledger, derived holdings, real daily prices | Market-shock news articles (AAPL, TSLA) |

The walkthrough below is industry-neutral. Wherever it says to ask the agent questions or set a system prompt, use your industry's versions from **[Appendix A](#appendix-a-per-industry-content)**.

---

## Prerequisites

You need a **Databricks workspace** with:

- Serverless SQL compute (or a running SQL warehouse)
- Foundation Model API access (Claude Sonnet 4, Llama 3.3 70B, or similar)
- Unity Catalog with permission to create schemas
- Vector Search enabled
- Databricks Apps enabled
- AI Gateway (Beta) — optional, Section 2 can be skipped if not enabled

**Permissions required:**

| Permission | Why |
|-----------|-----|
| `USE CATALOG` on your target catalog | Access existing catalog |
| `CREATE SCHEMA` on the catalog | Setup creates a new schema |
| `CREATE TABLE` on the new schema | Setup populates tables |
| Access to Foundation Model API | Agent and Playground need an LLM |
| Create Vector Search endpoints | Setup provisions a VS endpoint |

**No local tools required.** Everything runs in your browser through the Databricks workspace.

---

## Section 1: Codebase & Data Setup

**Time:** ~20 min (most of which is waiting for resources to provision)

This step creates the synthetic data, Vector Search index, Genie Space, and MLflow experiment that power the rest of the workshop.

### 1.1 Clone the Repository into Your Workspace

1. In your Databricks workspace, click **Workspace** in the left sidebar
2. Navigate to your user folder (`/Users/<your-email>/`)
3. Click the **...** menu > **Import**
4. Select **URL** and paste the repository URL:
   ```
   https://github.com/AnanyaDBJ/databricks-ai-workshops.git
   ```
5. Click **Import**

You should now see the full folder structure including `simple/`, `medium/`, `advanced/`, and `data/`.

### 1.2 Run the Data Setup Notebook

1. Navigate to `data/01_quickstart_setup.py`
2. Attach the notebook to **Serverless** compute (or any existing cluster)
3. Fill in the widgets at the top:
   - **Industry:** Pick your vertical — `retail`, `education`, or `financial_services`
   - **Catalog Name:** Your Unity Catalog (e.g., `ai_workshop_catalog`)
   - **Schema Name:** Choose a schema name (e.g., your name or team)
4. Click **Run All**

> **Sharing a workspace?** Retail and education create tables with the same names, so each attendee (or each industry) needs its **own schema** in the catalog.

> **Note:** The notebook takes 10-15 minutes to complete. Most of the time is spent provisioning the Vector Search endpoint.

> **Private Link / Firewall / Egress Restrictions:** If your workspace has network restrictions (Private Link, firewall rules, or blocked external egress), run the `data/00-utils.ipynb` notebook **before** running the setup notebook. This utility notebook creates an MLflow experiment with artifact storage configured as a Databricks Volume (avoiding external storage dependencies) and handles downloads through internal paths. Refer to the [workshop conductor document](https://docs.google.com/document/d/1BwcOXfQ0XBRHrPnzThwRcd4289cMheshSE6EKbTcnTw/edit) for detailed instructions on restricted-network setups.

### 1.3 What Gets Created

When the notebook finishes, you'll have (names depend on your industry):

| Resource | `retail` | `education` | `financial_services` |
|----------|----------|-------------|----------------------|
| Structured tables | customers, products, stores, transactions, transaction_items, payment_history | (same table names, education semantics) | clients, accounts, trades, portfolio_holdings, dailyprice, company_profile |
| Chunked docs table | `policy_docs_chunked` | `policy_docs_chunked` | `market_news_chunked` |
| Vector Search endpoint | `retail-vs-<schema>` | `education-vs-<schema>` | `fsi-vs-<schema>` |
| Vector Search index | `<catalog>.<schema>.policy_docs_index` | `<catalog>.<schema>.policy_docs_index` | `<catalog>.<schema>.market_news_index` |
| Genie Space | `FreshMart_Retail_Data_(<schema>)` | `EduPath_Academy_Data_(<schema>)` | `Financial_Services_Data_(<schema>)` |
| MLflow Experiment | `/Users/<you>/freshmart-agent-workshop` | `/Users/<you>/edupath-agent-workshop` | `/Users/<you>/meridian-agent-workshop` |
| UC Function | — | `student_forecast` | `weekly_close_spread` |

**Important:** Copy the output summary from the notebook. You'll need these values:
- **MLflow Experiment ID**
- **Vector Search Index name**
- **Genie Space ID**

### 1.4 Verify Resources

Before moving on, confirm:

- [ ] **Catalog Explorer:** Navigate to your catalog > schema — you should see the tables for your industry (plus the chunked docs table)
- [ ] **Vector Search:** Under **Compute** > **Vector Search Endpoints**, your endpoint should be ONLINE (or still provisioning — give it a few more minutes)
- [ ] **Genie:** Click **Genie** in the left sidebar — you should see your industry's Genie space (e.g., "EduPath_Academy_Data_(<schema>)")
- [ ] **Experiments:** Click **Experiments** in the left sidebar — you should see your experiment

---

## Section 2: AI Gateway (Beta)

**Time:** ~15 min

AI Gateway is the centralized governance and cataloging layer for all LLM interactions in your workspace. It sits between your applications and the model endpoints.

> **If AI Gateway Beta is not enabled in your workspace:** Skip this section entirely. The rest of the workshop works without it — your agent calls the Foundation Model API directly.

### 2.1 Navigate to AI Gateway

1. In the left sidebar, look for **AI Gateway** (under Machine Learning or as a top-level item)
2. Open the AI Gateway panel

### 2.2 Explore Key Capabilities

Walk through each feature:

| Feature | What It Does |
|---------|-------------|
| **Fallback Routing** | If the primary model is unavailable, automatically routes to a backup (e.g., Claude → Llama) |
| **Traffic Splitting** | A/B test models by routing a percentage of traffic to different endpoints |
| **Rate Limiting** | Prevent any single user or team from consuming all available capacity |
| **Payload Logging** | Record every prompt and response for compliance and debugging |
| **Guardrails** | Detect PII, block harmful content, enforce safety policies BEFORE responses reach users |
| **Metrics** | Real-time latency, throughput, and error rate monitoring |
| **Usage Dashboard** | Cost and token consumption broken down by user, team, or application |

### 2.3 Key Takeaway

Every LLM call in the workspace can be governed through this single control plane. When you deploy the agent in Section 4, its model calls route through AI Gateway automatically — giving you guardrails, logging, and cost tracking without any code changes.

---

## Section 3: Explore Platform Capabilities

**Time:** ~40 min

Now you'll explore the individual AI capabilities before combining them into an agent.

### 3.1 Play with Genie

Genie converts natural language questions into SQL queries and returns results from your data.

1. Click **Genie** in the left sidebar
2. Open your industry's Genie space (created in Section 1)
3. Try the **Genie questions for your industry from [Appendix A](#appendix-a-per-industry-content)**. Start with a simple count (e.g., "How many customers do we have?"), then work up to questions needing joins and aggregations.

**What to observe:**
- Genie shows the **SQL it generated** — click to inspect
- Results appear as tables or charts
- You can ask follow-up questions to refine ("Now show that as a monthly trend")
- Genie uses your Unity Catalog table schemas to understand the data model

### 3.2 Explore Vector Search

Vector Search finds relevant documents by meaning, not just keywords.

1. Open **Catalog** in the left sidebar
2. Navigate to your catalog > schema > your industry's index (`policy_docs_index`, or `market_news_index` for financial services)
3. Click **Query** on the index page
4. Try the **Vector Search queries for your industry from [Appendix A](#appendix-a-per-industry-content)** — each lists the source document it should retrieve

**What to observe:**
- Results include a **similarity score** (closer to 1.0 = better match)
- The search finds answers even with different wording (semantic search)
- Each result shows the text chunk and source document name

### 3.3 Prototype an Agent in Playground

This is where everything comes together.

1. Open **Playground** in the left sidebar (under Machine Learning)
2. Select a Foundation Model (e.g., **Claude Sonnet 4** or **Llama 3.3 70B**)
3. Click **Add Tool** and add:
   - Your **Genie Space** (from Section 1)
   - Your **Vector Search Index** (`policy_docs_index`, or `market_news_index` for financial services)
   - Your **UC Function** (if created in setup)
4. Add the **Playground system prompt for your industry from [Appendix A](#appendix-a-per-industry-content)**
5. Test one of each (exact questions in Appendix A):
   - A **data question** (should use Genie)
   - A **document question** (should use Vector Search)
   - A **multi-tool question** (should use both)

**What to observe:**
- The agent **automatically decides** which tool to use based on the question
- You can see the tool calls in the response
- The agent combines information from multiple tools naturally

### 3.4 Export to Databricks Apps

Once your agent is working in Playground:

1. Click the **"Get Code"** button (or "Export to App")
2. Select **OpenAI Agents SDK** as the template
3. Specify the MLflow experiment you created in Section 1
4. The generated code will be saved to your workspace

This exports a production-ready agent app with:
- The same model and tools configuration
- MLflow tracing built in
- A FastAPI server with chat UI
- Deployment configuration (`databricks.yml`)

> **Note:** You may see permission dialogs during export — the app needs a service principal to access your resources. See Troubleshooting if you encounter errors.

---

## Section 4: Databricks Apps — Custom Agent

**Time:** ~30 min

Now you have a full agent application. Let's deploy and test it.

### 4.1 Understand the App Architecture

The exported app (also available as `simple/L100-agent-openai-sdk/`) has this structure:

```
L100-agent-openai-sdk/
├── agent_server/
│   ├── agent.py          ← Agent logic: model, system prompt, MCP tools
│   ├── start_server.py   ← FastAPI server with MLflow tracing
│   ├── evaluate_agent.py ← Evaluation script
│   └── utils.py          ← Helpers
├── scripts/
│   ├── quickstart.py     ← One-command setup
│   └── start_app.py      ← Starts server + chat UI
├── databricks.yml        ← Deployment configuration
├── app.yaml              ← App settings
└── pyproject.toml        ← Python dependencies
```

The flow is:

```
Chat UI (browser) → FastAPI Server → OpenAI Agents SDK → MCP Tools
                                                          ├── Genie (data queries)
                                                          └── Vector Search (policy lookup)
                         ↓
                    MLflow Traces → Experiment
```

For detailed architecture, see [`L100-agent-openai-sdk/README.md`](./L100-agent-openai-sdk/README.md).

### 4.2 Deploy the App

**Option A: From the exported code (Section 3.4)**

If you used "Get Code" from Playground, the app is ready to deploy. Navigate to the app in Databricks Apps and wait for it to start.

**Option B: Deploy the pre-built template**

If you want to use the existing template in this repo:

1. Open a **Web Terminal** in your workspace (or use the Databricks CLI locally)
2. Navigate to the L100 agent folder:
   ```bash
   cd /Workspace/Users/<your-email>/databricks-ai-workshops/simple/L100-agent-openai-sdk
   ```
3. Configure the agent for your industry and workspace:
   ```bash
   uv run quickstart
   ```
   When prompted, pick your **industry** and enter the **catalog** and **schema** from Section 1. This writes your industry's system prompt and tool URLs into `agent_server/agent.py` and the Genie space grant into `databricks.yml`.
4. **Open `agent_server/agent.py` and read the generated block** — this is the heart of the workshop: one file containing the agent's name, system prompt, model, and MCP tool connections. Everything quickstart wrote is plain literal code you can edit.
5. Deploy:
   ```bash
   databricks bundle deploy
   databricks bundle run agent_openai_agents_sdk
   ```

> **Note:** First deployment takes 3-5 minutes. Subsequent deployments are faster.

### 4.3 Test the Agent

1. Once the app is running, open its URL (shown in Databricks Apps UI or in the deploy output)
2. The chat UI opens in your browser
3. Test with the **sample questions for your industry from [Appendix A](#appendix-a-per-industry-content)** — mix Genie questions, document questions, and multi-tool questions
4. Ask **5-10 questions** to generate enough traces for evaluation

### 4.4 Verify Traces Are Captured

1. Go to **Experiments** in the left sidebar
2. Open your experiment (e.g., `edupath-agent-workshop` — see Section 1.3 for your industry's name)
3. You should see new traces — one per conversation turn
4. Click on a trace to see the full execution graph

> **Troubleshooting:** If traces don't appear, verify the `MLFLOW_EXPERIMENT_ID` in the app's configuration matches your experiment.

---

## Section 5: MLflow Evals & Governance

**Time:** ~40 min

Now that you have traces, let's evaluate agent quality systematically.

### 5.1 Observability — Explore Traces

1. Open **Experiments** > your experiment
2. Click on any trace
3. Study the execution graph:

| Step | What to Look For |
|------|-----------------|
| **Input** | The user's question |
| **LLM Reasoning** | How the model decided which tool to call |
| **Tool Selection** | Which MCP tool was chosen and why |
| **Tool Call** | The actual request sent to Genie/Vector Search |
| **Tool Response** | The data returned from the tool |
| **Final Output** | The composed answer sent back to the user |

4. Check the **Latency** panel — note how long each step takes
5. Check **Token Usage** — this determines cost per interaction

**Key insight:** Observability gives you full traceability for debugging, compliance, security, and auditability.

### 5.2 Run the Evaluation Notebook

1. Navigate to `simple/01_simple_agent_evaluation.ipynb`
2. Attach to Serverless compute
3. Update the experiment name widget to match your experiment
4. Run the evaluation cells

The notebook uses these MLflow scorers:

| Scorer | What It Measures |
|--------|-----------------|
| Completeness | Did the agent fully answer the question? |
| RelevanceToQuery | Is the response relevant to what was asked? |
| Safety | Does the response avoid harmful content? |
| ToolCallEfficiency | Did the agent use tools efficiently (no unnecessary calls)? |
| Correctness | Is the factual content accurate? |

5. Review the results table — you'll see scores for each trace

### 5.3 Identify a Failure and Iterate

1. Look for a trace with a **low score** on any metric
2. Open that trace and understand WHY it scored poorly:
   - Did it call the wrong tool?
   - Was the response incomplete?
   - Did it hallucinate information?
3. Fix the issue by updating the system prompt in `agent_server/agent.py`

**Example fix:** If the agent fails to cite sources, add to the system prompt:
```
Always cite which tool provided the information. For data queries, mention that the answer came from the Genie Space. For policy questions, mention the source document name.
```

4. Redeploy the agent:
   ```bash
   databricks bundle deploy
   databricks bundle run agent_openai_agents_sdk
   ```
5. Ask the same question again and verify the improvement
6. Re-run evaluation to confirm the metric improved

**Key insight:** The cycle is: deploy → trace → evaluate → find failures → fix prompt/tools → redeploy → re-evaluate.

### 5.4 Understanding MLflow's Evaluation Platform

- **70+ built-in LLM judges** — no need to build custom evaluators
- **Managed and OSS:** Same API works with Databricks-hosted and open-source MLflow
- **Continuous monitoring:** Run evaluations on a schedule to catch regressions
- **Compare versions:** Evaluate different prompts/models side by side

---

## Section 6: Human in the Loop

**Time:** ~25 min

Automated judges are powerful, but human feedback is ground truth. This section shows how domain experts can review and rate agent responses.

### 6.1 Add Traces to a Labelling Session

1. Go to **Experiments** > your experiment
2. Select 5-10 traces (checkboxes on the left)
3. Click **Add to Labelling Session** (or "Create Review Task")
4. Name the session (e.g., "Workshop Review")

### 6.2 Configure the Labelling Schema

Define what reviewers should evaluate:

| Field | Type | Description |
|-------|------|-------------|
| Correctness | Rating (1-5) | Is the answer factually correct? |
| Helpfulness | Rating (1-5) | Would a real user find this useful? |
| Tool Usage | Yes/No | Did the agent use the right tool? |
| Notes | Free text | Any additional feedback |

### 6.3 Review Agent Responses

1. Navigate to the **Review App** (link shown after creating the session)
2. For each trace:
   - Read the user question and agent response
   - Rate correctness and helpfulness
   - Note if the agent used the wrong tool or missed information
   - Submit your review
3. Complete 3-5 reviews

### 6.4 Observe Feedback Integration

1. Go back to **Experiments** > your experiment
2. Open a trace you just reviewed
3. The human feedback is now attached to the trace metadata
4. This feedback can be used to:
   - Create evaluation datasets
   - Fine-tune the system prompt
   - Run automatic prompt optimization
   - Track quality trends over time

**Key insight:** Human review closes the loop: deploy → observe → human review → improve → redeploy.

---

## Section 7: Managed Agents

**Time:** ~25 min

Databricks offers no-code agent options that complement the custom agent you built in Section 4. These are ideal for simpler use cases or rapid prototyping.

### 7.1 Knowledge Assistant

A Knowledge Assistant is a RAG agent that answers questions from your documents — no code required.

1. Navigate to **Machine Learning** > **Agents** (or **Agent Builder**)
2. Click **Create** > **Knowledge Assistant**
3. Configure:
   - **Name:** e.g. "FreshMart Policy Assistant", "EduPath Policy Assistant", or "Meridian News Assistant"
   - **Knowledge Source:** Select your Vector Search index (`policy_docs_index`, or `market_news_index` for financial services)
   - Optionally: point to the raw documents volume for richer rendering
4. Click **Create**
5. Test it with 2-3 of the **document questions for your industry from [Appendix A](#appendix-a-per-industry-content)** and check that the expected source document is retrieved

**What to notice:** This achieves the same thing as your Vector Search tool in the custom agent — but with zero code and a managed hosting model.

### 7.2 Supervisor Agent (Multi-Agent System)

A Supervisor Agent orchestrates multiple tools/agents, routing questions to the right one automatically.

1. Create a **Supervisor Agent**
2. Add these tools:
   - **Genie MCP** — your industry's Genie space
   - **Vector Search MCP** — your industry's index
   - **UC Function MCP** — if available
3. Add a description and instructions
4. Test with the **multi-tool questions for your industry from [Appendix A](#appendix-a-per-industry-content)** and watch which tool each question routes to

### 7.3 Comparing Approaches

| Aspect | Custom Agent (Section 4) | Managed Agents (Section 7) |
|--------|-------------------------|---------------------------|
| **Code required** | Yes (Python, YAML) | No |
| **Customization** | Full control | Limited to configuration |
| **UI** | Custom chat app | Built-in interface |
| **Deployment** | Databricks Apps | Managed hosting |
| **Use case** | Production apps, complex logic | Quick prototypes, simple Q&A |
| **Tracing** | Full MLflow integration | Built-in observability |

Both are production-ready. Choose based on your needs: simple use cases get managed agents, complex workflows get custom apps.

---

## Section 8: Document Intelligence (Optional)

**Time:** ~15 min

> **Coming Soon** — This section is under development. Document Intelligence enables intelligent parsing of complex PDFs (tables, forms, scanned images) beyond simple text chunking. Check back for detailed instructions.

---

## Troubleshooting

### Common Issues

| Issue | Section | Solution |
|-------|---------|----------|
| "Please enter a catalog name" error | 1 | Fill in the Catalog Name widget before running |
| Tables overwritten by another attendee | 1 | Retail and education share table names — each setup run needs its own schema |
| Agent answers about the wrong industry | 4 | Re-run `uv run quickstart` and pick the industry you set up in Section 1 |
| Quickstart can't find the Genie space | 4 | Paste the space ID from the setup notebook's summary (or the Genie space URL) when prompted |
| Setup notebook can't find policy docs | 1 | Import the FULL repository, not just the `simple/` folder |
| Vector Search endpoint stuck provisioning | 1 | Wait up to 15 minutes. Check **Compute** > **Vector Search Endpoints** |
| "No SQL warehouse found" | 1 | Create a serverless SQL warehouse or start an existing one |
| AI Gateway not visible in sidebar | 2 | Beta not enabled in your workspace — skip Section 2 |
| Genie not answering questions | 3 | Verify the SQL warehouse linked to the Genie Space is running |
| Vector Search returns no results | 3 | Index sync may still be in progress — wait a few minutes |
| Playground doesn't show tools | 3 | Re-add tools; confirm VS index is ONLINE |
| "Get Code" export fails | 3 | Check you have workspace write permissions; see permission dialog |
| App crashes on startup | 4 | Check logs: `databricks apps logs <app-name>`. Likely service principal permissions |
| App returns errors | 4 | Verify resource permissions in `databricks.yml` match actual resources |
| No traces in experiment | 5 | Verify `MLFLOW_EXPERIMENT_ID` in app config matches your experiment |
| Evaluation notebook errors | 5 | Ensure experiment has traces with status `OK` (not failed traces) |
| Labelling session is empty | 6 | Select traces first, THEN create the session |
| Knowledge Assistant returns nothing | 7 | VS index must be ONLINE and synced |
| Permission denied on catalog | All | Ask workspace admin for `CREATE SCHEMA` and `USE CATALOG` permissions |

### Getting Help

- **Workshop setting:** Ask your instructor
- **Self-paced:** Check the [Databricks documentation](https://docs.databricks.com) or [community forums](https://community.databricks.com)
- **Permission issues:** Contact your workspace administrator

---

## Appendix A: Per-Industry Content

All industry-specific content lives here: the Playground system prompt, sample questions for each tool, and prompt variations for the iteration exercise in Section 5.3. Use the subsection matching the industry you picked in Section 1.

> The deployed app's system prompt in `agent_server/agent.py` is written automatically by `uv run quickstart` (Section 4.2) — the prompts below are for the **Playground** prototype and for experimenting.

---

### A.1 Retail — FreshMart

**Playground system prompt:**
```
You are FreshMart Assistant, a friendly and knowledgeable retail agent for FreshMart grocery stores. You help customers and employees with data questions about products, sales, and stores, as well as store policy inquiries.

Guidelines:
- Be conversational and helpful
- Ground all answers in retrieved data — never fabricate information
- Cite your sources (which tool provided the data)
- For data questions, use Genie to query the database
- For policy questions, use Vector Search to find relevant documents
- Be concise but thorough
```

**Data queries (Genie):**
1. "How many customers do we have?"
2. "What are the top 10 products by price?"
3. "Show revenue by store for the last 6 months"
4. "Which membership tier spends the most on average?"
5. "What's the average transaction value per day of week?"
6. "List all organic products under $5"
7. "What payment methods are most popular?"
8. "Show me payment method distribution by membership tier"

**Policy lookups (Vector Search):**

| Query | Expected Source Document |
|-------|------------------------|
| "What is the return policy for perishable items?" | return_refund_policy |
| "How do I earn loyalty points?" | membership_loyalty_program |
| "What are your delivery hours and zones?" | delivery_pickup_procedures |
| "Do you accept EBT or SNAP benefits?" | store_operating_procedures |
| "How do you handle product recalls?" | product_safety_recalls |
| "What personal data do you collect?" | privacy_policy |
| "How should staff handle complaints?" | customer_service_guidelines |

**Multi-tool questions (both):**
1. "I bought frozen fish and it was bad — can I return it? How much revenue do we lose to returns?"
2. "What are our most popular products and what's the return policy for them?"
3. "Which stores have the lowest ratings, and what does our customer service policy say about complaints?"
4. "Show me high-value customers and explain what loyalty benefits they get"
5. "What categories drive the most revenue, and do we have safety policies for those product types?"

**Edge cases (test agent limits):**
1. "What's the weather like today?" (out of scope)
2. "Delete all customer records" (should refuse)
3. "Tell me about competitor pricing" (no data available)

**System prompt variations (for Section 5.3 iteration):**
- *Concise:* "You are FreshMart Assistant. Answer questions using Genie (data) and Vector Search (policies). Be brief and cite your sources."
- *Customer-facing:* "You are a friendly FreshMart customer service agent. Help customers with questions about products, orders, returns, and store policies. Always be empathetic and solution-oriented. Use Genie for order/product lookups and Vector Search for policy information."
- *Internal analytics:* "You are an analytics assistant for FreshMart management. Provide data-driven insights about sales, customer behavior, and store performance. When asked about policies, reference the official documents. Always include relevant numbers and trends."

---

### A.2 Education — EduPath Academy

**Playground system prompt:**
```
You are EduPath Assistant, a friendly and knowledgeable agent for EduPath Academy, a higher-education institution. You help students and staff with data questions about courses, enrollments, and campuses, as well as academic policy inquiries.

Guidelines:
- Be conversational and helpful
- Ground all answers in retrieved data — never fabricate information
- Cite your sources (which tool provided the data)
- For data questions, use Genie to query the database
- For policy questions, use Vector Search to find relevant documents
- Be concise but thorough
```

**Data queries (Genie):**
1. "How many students do we have?"
2. "What are the top 10 courses by tuition?"
3. "Show enrollment revenue by campus for the last 6 months"
4. "Which student tier spends the most on average?"
5. "What's the average transaction value per day of week?"
6. "List all Computer Science courses"
7. "What payment methods are most popular?"
8. "How many students pay with financial aid or scholarships?"

**Policy lookups (Vector Search):**

| Query | Expected Source Document |
|-------|------------------------|
| "How is my final grade calculated?" | grading_policy |
| "What happens if I miss too many classes?" | attendance_policy |
| "How do I enroll in a course?" | course_enrollment |
| "Can I get a tuition refund if I withdraw?" | tuition_refund |
| "What counts as plagiarism?" | academic_integrity |
| "What are the rules on student behavior?" | student_conduct |
| "What personal data do you collect about students?" | privacy_policy |

**Multi-tool questions (both):**
1. "I want to withdraw from my most expensive course — what refund would I get?"
2. "Which courses have the highest enrollment, and what's the attendance policy for them?"
3. "Show me students paying with financial aid and explain the tuition refund rules that apply to them"
4. "Which campus generates the most revenue, and what does the enrollment policy say about transferring campuses?"
5. "What departments drive the most enrollments, and what are the grading rules for their courses?"

**Edge cases (test agent limits):**
1. "What's the weather like today?" (out of scope)
2. "Delete all student records" (should refuse)
3. "How does our tuition compare to other universities?" (no data available)

**System prompt variations (for Section 5.3 iteration):**
- *Concise:* "You are EduPath Assistant. Answer questions using Genie (data) and Vector Search (academic policies). Be brief and cite your sources."
- *Student-facing:* "You are a friendly EduPath Academy student services agent. Help students with questions about courses, enrollment, tuition, and academic policies. Always be empathetic and solution-oriented. Use Genie for course/enrollment lookups and Vector Search for policy information."
- *Internal analytics:* "You are an analytics assistant for EduPath Academy administrators. Provide data-driven insights about enrollment, student behavior, and campus performance. When asked about policies, reference the official documents. Always include relevant numbers and trends."

---

### A.3 Financial Services — Meridian Capital Partners

> **How the Meridian data fits together:** the `trades` table is a simulated buy/sell ledger executed on real trading dates at real closing prices (from the snapshotted Marketplace `dailyprice`). `portfolio_holdings` (quantity, average cost, realized/unrealized P&L) and account cash balances are **derived from that ledger**, so exposure questions, trade-history questions, and price questions all reconcile. Clients also react to real market shocks — risk-averse clients sell after big drops, risk-seeking ones buy the dip — which is what makes the multi-tool questions below interesting.

**Playground system prompt:**
```
You are Meridian Assistant, a knowledgeable agent for Meridian Capital Partners, an investment management firm. You help analysts with data questions about clients, accounts, the trade ledger, portfolio holdings, and market prices, as well as market news research.

Guidelines:
- Be conversational and helpful
- Ground all answers in retrieved data — never fabricate information
- Cite your sources (which tool provided the data)
- For client, portfolio, and price questions, use Genie to query the database
- For market news and historical events, use Vector Search to find relevant articles
- Never offer personalized investment advice
- Be concise but thorough
```

**Data queries (Genie):**
1. "How many clients do we have?"
2. "What are the largest portfolio holdings by market value?"
3. "Show AAPL's closing price over the last 30 days"
4. "Which clients have a High risk rating?"
5. "What's our net exposure to TSLA across all portfolios?"
6. "Which accounts have the largest unrealized losses?"
7. "Who were the most active traders last quarter?"
8. "What was TSLA's biggest single-day price drop?"
9. "Show total realized P&L by client, best to worst"
10. "What's the total market value of holdings by account type?"

**Market news lookups (Vector Search):**

| Query | Expected Source Document |
|-------|------------------------|
| "News about tariffs hitting tech stocks" | tech_stocks_sink_trump_tariffs / apple_shares_fall_trump_tariffs |
| "What happened when the DOJ sued Apple?" | doj_sues_apple_iphone_monopoly |
| "Tesla robotaxi announcement" | tesla_cybercab_robotaxi_reveal |
| "Musk's compensation package ruling" | musk_56b_tesla_comp_voided |
| "Apple Vision Pro launch coverage" | apple_vision_pro_launch |
| "COVID impact on iPhone production" | apple_covid_china_iphone |
| "Tesla price cuts in the US and Europe" | tesla_cuts_prices_us_europe |

**Multi-tool questions (both):**
1. "How did AAPL's price move around the tariff announcement, and what did the news say at the time?"
2. "Which clients sold TSLA in the days after its biggest price drop, and what did the news report that week?"
3. "Which clients hold TSLA today, and what recent news could affect their positions?"
4. "What's our total exposure to Apple across all portfolios, and what regulatory risks does the news mention?"
5. "Did any clients buy the dip after the tariff sell-off? What was the news context?"
6. "Compare TSLA's volatility this month with the market events reported in the news" (also exercises the `weekly_close_spread` UC function if added as a tool)

**Edge cases (test agent limits):**
1. "What's the weather like today?" (out of scope)
2. "Delete all client records" (should refuse)
3. "Should I buy Apple stock?" (should decline personalized investment advice)

**System prompt variations (for Section 5.3 iteration):**
- *Concise:* "You are Meridian Assistant. Answer questions using Genie (client and market data) and Vector Search (market news). Be brief, cite your sources, and never give personalized investment advice."
- *Client-reporting:* "You are an assistant helping Meridian Capital relationship managers prepare client updates. Summarize portfolio positions and relevant market news in plain language a client can understand. Use Genie for positions and prices, Vector Search for news context. Never give personalized investment advice."
- *Research analyst:* "You are a research assistant for Meridian Capital analysts. Provide data-driven insights on price movements, holdings concentration, and risk exposure, connecting them to historical market-shock events from the news archive. Always include relevant numbers and dates."

**Agentic event-analysis prompt (advanced):** hand the Genie space, the Vector Search index, and the `weekly_close_spread` UC function to one agent and give it a multi-step workflow — news event in, documented trade recommendation out (modeled on the agentic bond-trading-monitoring demo pattern). The full prompt lives in the code at [`L100-agent-openai-sdk/scripts/industries.py`](./L100-agent-openai-sdk/scripts/industries.py) (the `agentic_system_prompt` key under `financial_services`) — paste it into the Playground or into `agent.py`'s `SYSTEM_PROMPT`. Try it with: *"Apple just priced its first bond offering in two years amid tariff uncertainty — analyze the impact on our portfolio."*
