# Build Your First AI Agent on Databricks

Create a conversational AI assistant for a fictional grocery chain called **FreshMart** — using only managed Databricks services, no coding required after setup.

---

## What You'll Build

| Capability | Powered By | Example |
|---|---|---|
| **Ask questions about data** | Genie Space | "What are the top 5 products by revenue?" |
| **Look up store policies** | Vector Search | "What is the return policy for perishable items?" |
| **Conversational AI agent** | Playground / Agent Builder | Combines both tools into a single chat experience |
| **Evaluate agent quality** | MLflow Experiment | Review traces, latency, and quality scores |

The setup notebook creates synthetic FreshMart data — customers, products, stores, transactions, and policy documents — so you can focus on building and exploring, not on data preparation.

---

## Prerequisites

You need a **Databricks workspace** with:

- Serverless SQL compute
- Foundation Model API (Claude or Llama)
- Unity Catalog
- Vector Search
- A catalog you can create schemas in

No local tools are required. Everything runs in your browser through the Databricks workspace.

---

## Quick Start

### 1. Clone the repository into your workspace

In your Databricks workspace:

1. Click **Workspace** in the left sidebar
2. Navigate to your user folder
3. Click **...** > **Import**
4. Select **URL** and paste: `https://github.com/AnanyaDBJ/databricks-ai-workshops.git`
5. Click **Import**

### 2. Open the setup notebook

Navigate to `simple/00_quickstart_setup.py` in the imported repository.

### 3. Configure and run

1. Attach the notebook to a **serverless** compute or an existing cluster
2. Fill in your **Catalog Name** in the widget at the top of the notebook (the schema defaults to `retail_grocery`)
3. Click **Run All**

The notebook takes about 10-15 minutes to complete. It will print a summary of everything it created.

---

## What the Setup Creates

### Data Tables

| Table | Rows | Description |
|---|---|---|
| `customers` | 200 | Shopper profiles with membership tiers and dietary preferences |
| `products` | ~500 | Grocery items across 10 categories (Produce, Dairy, Bakery, etc.) |
| `stores` | 10 | FreshMart store locations with ratings and employee counts |
| `transactions` | 2,000 | Purchase records linked to customers and stores |
| `transaction_items` | ~8,000 | Line items for each transaction with quantities and prices |
| `payment_history` | 400 | Payment method records per customer |
| `policy_docs_chunked` | ~50 | 7 store policy documents split into searchable chunks |

### Databricks Resources

| Resource | Name | Purpose |
|---|---|---|
| Vector Search Endpoint | `freshmart-vs-<schema>` | Compute that powers similarity search |
| Vector Search Index | `<catalog>.<schema>.policy_docs_index` | Searchable index over policy document chunks |
| Genie Space | `FreshMart Retail Data (<schema>)` | Natural language interface to the 6 data tables |
| MLflow Experiment | `/Users/<you>/freshmart-agent-workshop` | Tracks agent traces and evaluation metrics |

---

## Workshop Module 1: Explore Your Data with Genie

Genie converts plain English questions into SQL queries and returns results from your data tables.

### Open your Genie Space

1. Click **Genie** in the left sidebar
2. Open **FreshMart Retail Data** (the space created by the setup notebook)

### Try these questions

| Question | What it does |
|---|---|
| "How many customers do we have?" | Counts rows in the customers table |
| "What are the top 10 products by price?" | Queries and sorts the products table |
| "Show me revenue by store for the last 6 months" | Joins transactions, items, and stores |
| "Which membership tier spends the most on average?" | Groups customers by tier with transaction totals |
| "What payment methods are most popular?" | Aggregates payment_history data |
| "List all organic products in the Produce category" | Filters products by name and category |

### What to notice

- Genie shows the **SQL query** it generated — click on it to see exactly how your question was translated
- Results appear as **tables** and sometimes **charts**
- You can ask follow-up questions to refine results ("Now show that as a monthly trend")
- Genie uses your Unity Catalog table schemas to understand column names and relationships

---

## Workshop Module 2: Search Policy Documents with Vector Search

Vector Search finds relevant documents using meaning, not just keywords. It converts your question into an embedding (a numerical representation) and finds the most similar document chunks.

### Explore the Vector Search index

1. Open **Catalog** in the left sidebar
2. Navigate to your catalog > schema > **policy_docs_index**
3. You'll see the index metadata including the source table and embedding model

### Run a similarity search

1. In **Catalog Explorer**, click on the `policy_docs_index`
2. Click **Query** (or use the Vector Search query UI)
3. Enter a question like: `"What is the return policy for frozen food?"`
4. Review the returned chunks — they come from the most relevant policy documents

### Example queries to try

| Query | Expected source document |
|---|---|
| "Can I return perishable items?" | return_refund_policy |
| "How do I earn loyalty points?" | membership_loyalty_program |
| "What are your delivery hours?" | delivery_pickup_procedures |
| "Do you accept EBT payments?" | store_operating_procedures |
| "How do you handle product recalls?" | product_safety_recalls |
| "What data do you collect about me?" | privacy_policy |

### What to notice

- Results include a **similarity score** — closer to 1.0 means a better match
- The search finds answers even if your question uses different words than the document (semantic search)
- Each result shows the **chunk** of text that matched, along with the source document name

---

## Workshop Module 3: Build Your First AI Agent

Now combine Genie (data queries) and Vector Search (policy lookup) into a single conversational agent.

### Option A: Databricks Playground (quickest)

1. Go to **Playground** in the left sidebar (under Machine Learning)
2. Select a Foundation Model — for example, **Claude Sonnet 4** or **Llama 3.3 70B**
3. Click **Add Tool** and add:
   - Your **Genie Space** (FreshMart Retail Data)
   - Your **Vector Search Index** (policy_docs_index)
4. Start chatting with your agent

### Example conversations

Try these to see both tools in action:

> **You:** What are your store hours on holidays?
>
> *The agent uses Vector Search to find the answer in the store_operating_procedures policy document.*

> **You:** What are the top 5 selling products?
>
> *The agent uses Genie to query the transactions and products tables.*

> **You:** I bought some frozen fish yesterday and it was bad. Can I return it? What's the refund process?
>
> *The agent uses Vector Search to look up the return policy for perishable/frozen items.*

> **You:** Which stores have the highest average transaction value?
>
> *The agent uses Genie to join transactions with stores and compute averages.*

### Option B: AI Agent Builder (full-featured)

For a more structured agent setup:

1. Go to **Machine Learning** > **Agents** in the left sidebar
2. Click **Create Agent**
3. Choose a Foundation Model
4. Add your tools (Genie Space, Vector Search Index)
5. Customize the system prompt to define the agent's personality (e.g., "You are a helpful FreshMart grocery assistant...")
6. Test and iterate in the builder UI
7. Optionally save and register the agent

### What to notice

- The agent **automatically decides** which tool to use based on your question
- Data questions go to Genie, policy questions go to Vector Search
- You can see the **tool calls** the agent made in the conversation trace
- The agent can combine information from both tools in a single response

---

## Workshop Module 4: Evaluate Your Agent

MLflow helps you understand how well your agent is performing.

### View traces

1. Go to **Experiments** in the left sidebar
2. Open your experiment: **freshmart-agent-workshop**
3. If you tested your agent in the Playground with tracing enabled, you'll see traces here
4. Click on a trace to see the full execution: input, tool calls, LLM reasoning, and output

### What to look for in traces

| Element | What it tells you |
|---|---|
| **Latency** | How long each step took (LLM call, tool call, total) |
| **Tool calls** | Which tools the agent chose and what parameters it passed |
| **LLM input/output** | The full prompt sent to the model and its response |
| **Token usage** | How many tokens were consumed (affects cost) |

### Running evaluations (optional)

If you want to systematically evaluate your agent, the advanced tier includes an evaluation suite with 9 MLflow scorers covering completeness, safety, fluency, and more. See the `advanced/` directory for details.

---

## What's Next

This workshop covered the fundamentals using managed Databricks services. To go deeper:

| Tier | What you'll learn | Directory |
|---|---|---|
| **Advanced** | Build a full LangGraph agent with MCP tools, Lakebase memory, and deploy to Databricks Apps | `advanced/` |

The advanced tier adds:
- **Long-term memory** — the agent remembers user preferences across sessions using Lakebase (managed PostgreSQL)
- **Custom tool orchestration** — LangGraph for multi-step agent workflows with MCP (Model Context Protocol)
- **Production deployment** — Deploy as a Databricks App with OAuth authentication and streaming chat UI
- **Agent evaluation** — 9 automated scorers using MLflow, plus human-in-the-loop review

---

## Troubleshooting

| Issue | Solution |
|---|---|
| "Please enter a catalog name" error | Fill in the **Catalog Name** widget at the top of the notebook before running |
| Notebook can't find policy docs | Make sure you imported the full repository (not just the `simple/` folder) |
| Vector Search endpoint stuck provisioning | Wait up to 15 minutes. If still not ONLINE, check the Vector Search UI under **Compute** |
| "No SQL warehouse found" | Create a serverless SQL warehouse or start an existing one before running the Genie Space cell |
| Genie Space not answering questions | Verify the SQL warehouse linked to the Genie Space is running |
| Vector Search returns no results | The index sync may still be in progress — wait a few minutes and try again |
| Permission denied on catalog | Ask your workspace admin for `CREATE SCHEMA` and `USE CATALOG` permissions |
| Playground doesn't show tools | Make sure you added the Genie Space and Vector Search Index as tools in the Playground |
| MLflow experiment not showing traces | Verify tracing is enabled in your Playground session |
