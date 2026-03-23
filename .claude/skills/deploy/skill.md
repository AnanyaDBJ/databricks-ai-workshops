# Deploy Agent to Databricks Apps

Deploy the agent as a Databricks App with all required resources.

## Prerequisites

- Databricks CLI authenticated (`databricks auth login`)
- All environment variables configured in `.env`
- Agent tested locally (`uv run start-app`)

## Deployment Steps

### 1. Create the App

```bash
databricks apps create retail-grocery-ltm-memory
```

### 2. Add Resources via UI

Go to your Databricks workspace > Apps > retail-grocery-ltm-memory > Edit > App Resources:

| Resource | Type | Permission |
|---|---|---|
| MLflow Experiment | experiment | CAN_MANAGE |
| Genie Space | genie_space | CAN_RUN |
| Lakebase Instance | database | CAN_CONNECT_AND_CREATE |
| Vector Search Index | uc_securable (TABLE) | SELECT |

### 3. Grant Lakebase Permissions

After adding Lakebase as a resource, grant schema permissions to the app's service principal:

```bash
uv run python scripts/grant_lakebase_permissions.py
```

Or manually run the SQL from the README against your Lakebase instance.

### 4. Sync Code to Workspace

```bash
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks sync . "/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory"
```

### 5. Deploy

```bash
databricks apps deploy retail-grocery-ltm-memory \
  --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory
```

### 6. Verify Deployment

```bash
# Get OAuth token
databricks auth token

# Test the deployed agent
curl -X POST <app-url>.databricksapps.com/invocations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "hi"}], "stream": true}'
```

## Using Databricks Asset Bundles (Alternative)

The `databricks.yml` file defines the bundle configuration. Update the TODO placeholders with your values, then:

```bash
databricks bundle deploy -t dev
```

## Redeployment

For subsequent updates:

```bash
databricks sync . "/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory"
databricks apps deploy retail-grocery-ltm-memory \
  --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/retail-grocery-ltm-memory
```

## Troubleshooting

- **302 error when querying**: Use OAuth token, not PAT
- **Permission denied on Lakebase**: Run the grant permissions script
- **App fails to start**: Check app logs in the Databricks UI for missing env vars
