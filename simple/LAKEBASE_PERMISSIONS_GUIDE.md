# Lakebase Permissions Guide for Model Serving Deployment

## Context

When deploying a stateful agent (with LangGraph `CheckpointSaver`) to **Databricks Model Serving** using a **Lakebase Autoscaling** project, the endpoint's auto-created service principal needs explicit Postgres permissions.

This is required because `DatabricksLakebase` (the MLflow resource class) only supports **Provisioned** instances for automatic auth passthrough. For Autoscaling projects, you must manually grant permissions to the endpoint's service principal.

## Project Details

| Setting | Value |
| --- | --- |
| Lakebase Project | `<your-project-name>` |
| Branch | `production` |
| Endpoint | `projects/<your-project-name>/branches/production/endpoints/primary` |
| Host | `<your-endpoint-host>.database.<region>.azuredatabricks.net` |
| Model Serving Endpoint | `agents_<your-endpoint-name>` |
| Endpoint Service Principal | `<sp-client-id>` |

## Permissions Granted

### Step 1: Create Postgres Role for the Service Principal

Run in the **Lakebase SQL Editor** (or via any Postgres connection to the project):

```sql
-- Enable OAuth authentication extension
CREATE EXTENSION IF NOT EXISTS databricks_auth;

-- Create a Postgres role for the endpoint's service principal
SELECT databricks_create_role('<sp-client-id>', 'SERVICE_PRINCIPAL');

-- Grant database connection
GRANT CONNECT ON DATABASE databricks_postgres TO "<sp-client-id>";

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO "<sp-client-id>";

-- Grant all on schema (for creating tables if needed)
GRANT ALL ON SCHEMA public TO "<sp-client-id>";
```

### Step 2: Grant Checkpoint Table Permissions

The `CheckpointSaver` creates 4 tables in the `public` schema. The endpoint SP needs access to all of them:

```sql
-- Grant permissions on checkpoint tables
GRANT ALL ON TABLE checkpoints TO "<sp-client-id>";
GRANT ALL ON TABLE checkpoint_blobs TO "<sp-client-id>";
GRANT ALL ON TABLE checkpoint_writes TO "<sp-client-id>";
GRANT ALL ON TABLE checkpoint_migrations TO "<sp-client-id>";

-- Grant default privileges for any future tables created in public schema
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON TABLES TO "<sp-client-id>";
```

## How to Find the Endpoint Service Principal ID

When a deployment fails with a Postgres authentication error, the service principal ID appears in the **service logs**:

```
password authentication failed for user '<SP-CLIENT-ID>'
```

You can also retrieve it from the endpoint service logs:

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
logs = w.serving_endpoints.logs(
    name="<endpoint-name>",
    served_model_name="<served-model-name>"
)
print(logs.logs[-2000:])  # Look for the user ID in auth failure messages
```

## Why This Is Needed

| Lakebase Type | Auth Passthrough | Manual Grants Needed? |
| --- | --- | --- |
| **Provisioned** | Automatic via `DatabricksLakebase` resource | No |
| **Autoscaling** | Not yet supported by `DatabricksLakebase` | **Yes** |

For Autoscaling projects:
1. The MLflow `DatabricksLakebase` resource class only accepts `database_instance_name` (Provisioned)
2. Without it, Model Serving still creates an SP and injects OAuth tokens
3. But it does NOT auto-create the Postgres role or grant table permissions
4. You must manually create the role and grant access (Steps 1 & 2 above)

## Programmatic Grant (from notebook)

Instead of using the SQL Editor, you can grant permissions from a notebook using your own credentials:

```python
from databricks_langchain import CheckpointSaver

sp_id = "<sp-client-id>"  # Get this from the service logs (see above)

with CheckpointSaver(
    project="<your-project-name>",
    branch="production"
) as saver:
    pool = saver._lakebase.pool
    with pool.connection() as conn:
        conn.execute(f'GRANT ALL ON TABLE checkpoints TO "{sp_id}"')
        conn.execute(f'GRANT ALL ON TABLE checkpoint_blobs TO "{sp_id}"')
        conn.execute(f'GRANT ALL ON TABLE checkpoint_writes TO "{sp_id}"')
        conn.execute(f'GRANT ALL ON TABLE checkpoint_migrations TO "{sp_id}"')
        conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{sp_id}"')
        conn.execute(f'GRANT USAGE ON SCHEMA public TO "{sp_id}"')
        print(f"Granted all permissions to SP {sp_id}")
```

## Redeployment Notes

- If you **redeploy** the model (new version), the endpoint may get a **new service principal ID**. You'll need to repeat the grants for the new SP.
- If you only **update the model version** on the same endpoint config, the SP remains the same.
- Consider granting permissions to a Postgres **group role** and adding each new SP to that group for easier management.

## Verification

Test the endpoint after granting permissions:

```python
import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
host = w.config.host.rstrip("/")
token = w.config._header_factory()["Authorization"].replace("Bearer ", "")

endpoint_name = "<your-endpoint-name>"
url = f"{host}/serving-endpoints/{endpoint_name}/invocations"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

response = requests.post(url, headers=headers, json={
    "input": [{"role": "user", "content": "Hello!"}],
    "custom_inputs": {"thread_id": "test-permissions"}
}, timeout=60)

print(response.status_code, response.json())
```
