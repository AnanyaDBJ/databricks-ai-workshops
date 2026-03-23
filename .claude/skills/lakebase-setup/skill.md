# Lakebase Setup

Configure Lakebase (managed PostgreSQL) for agent memory, checkpoints, and chat history.

## What Lakebase Is Used For

| Feature | Schema | Tables |
|---|---|---|
| Agent checkpoints | `public` | `store`, `store_migrations`, `store_vectors`, `vector_migrations` |
| User memories | `public` | `store`, `store_vectors` (namespaced by user_id) |
| Chat history (UI) | `ai_chatbot` | Chat, Message tables via Drizzle ORM |
| DB migrations | `drizzle` | Migration metadata |

## Setup Options

### Option 1: Via Quickstart (Recommended)

```bash
uv run quickstart
```

The quickstart script will prompt you to create or select a Lakebase instance.

### Option 2: Manual Setup

#### Create a Lakebase Instance

In the Databricks UI: SQL > Lakebase > Create Instance

Or via CLI:
```bash
databricks database create-instance --name my-lakebase-instance
```

#### Configure Environment

Add to `.env`:
```
LAKEBASE_INSTANCE_NAME=my-lakebase-instance
PGHOST=instance-xxx.database.xxx.cloud.databricks.com
PGUSER=your-email@domain.com
PGDATABASE=databricks_postgres
```

### Option 3: Autoscaling Lakebase

For autoscaling instances, set:
```
LAKEBASE_AUTOSCALING_PROJECT=your-project
LAKEBASE_AUTOSCALING_BRANCH=your-branch
```

## Granting Permissions for Deployment

When deploying to Databricks Apps, the app's service principal needs access:

1. Add Lakebase as an app resource (UI: App > Edit > App Resources > Add > Database)
2. Run the permission grant script:

```bash
uv run python scripts/grant_lakebase_permissions.py
```

Or manually execute the SQL:

```sql
DO $$
DECLARE
   app_sp text := 'your-app-sp-id';
BEGIN
   -- Drizzle schema
   EXECUTE format('GRANT USAGE, CREATE ON SCHEMA drizzle TO %I;', app_sp);
   EXECUTE format('GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA drizzle TO %I;', app_sp);

   -- App schema
   EXECUTE format('GRANT USAGE, CREATE ON SCHEMA ai_chatbot TO %I;', app_sp);
   EXECUTE format('GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ai_chatbot TO %I;', app_sp);

   -- Public schema (checkpoints + memory store)
   EXECUTE format('GRANT USAGE, CREATE ON SCHEMA public TO %I;', app_sp);
   EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE public.store_migrations TO %I;', app_sp);
   EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE public.store TO %I;', app_sp);
   EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE public.store_vectors TO %I;', app_sp);
   EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE public.vector_migrations TO %I;', app_sp);
END $$;
```

## How Memory Storage Works

- Uses `AsyncDatabricksStore` from `databricks-langchain[memory]`
- Embeddings generated via `databricks-gte-large-en` (1024 dims)
- Memories are namespaced by `user_id` for per-user isolation
- Semantic search uses cosine similarity on embeddings

## Troubleshooting

- **"Lakebase configuration is required"**: Set `LAKEBASE_INSTANCE_NAME` or autoscaling vars in `.env`
- **Permission denied**: Run the grant permissions script above
- **Connection refused**: Verify `PGHOST` points to the correct Lakebase hostname
- **Hostname vs instance name confusion**: The code auto-resolves hostnames to instance names
