# Quickstart Setup

Set up the development environment and configure all Databricks resources.

## Steps

### 1. Check Prerequisites

```bash
# Verify uv is installed
uv --version

# Verify nvm and Node.js 20
nvm --version
node --version  # should be v20.x

# Verify Databricks CLI
databricks --version
```

If any are missing:
- uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- nvm: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash` then `nvm install 20`
- Databricks CLI: `curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh`

### 2. Run the Quickstart Script

```bash
uv run quickstart
```

This interactive script will:
1. Authenticate with Databricks via OAuth
2. Create an MLflow experiment for tracing
3. Configure Lakebase (provisioned or autoscaling)
4. Set up Genie Space and Vector Search index
5. Generate the `.env` file

### 3. Manual Setup (if quickstart fails)

```bash
# Authenticate
databricks auth login

# Create MLflow experiment
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks experiments create-experiment /Users/$DATABRICKS_USERNAME/agents-on-apps

# Copy and fill environment variables
cp .env.example .env
# Edit .env with your values
```

### 4. Start the Application

```bash
uv run start-app
```

- Chat UI: http://localhost:3000
- API: http://localhost:8000

## Environment Variables Reference

| Variable | Description | Example |
|---|---|---|
| `DATABRICKS_CONFIG_PROFILE` | Databricks CLI auth profile | `DEFAULT` |
| `MLFLOW_EXPERIMENT_ID` | MLflow experiment for tracing | `123456789` |
| `LAKEBASE_INSTANCE_NAME` | Lakebase PostgreSQL instance | `my-lakebase` |
| `GENIE_SPACE_ID` | Genie space for data queries | `01ef...` |
| `VECTOR_SEARCH_INDEX` | Vector search index path | `catalog/schema/index` |
| `PGHOST` | Lakebase hostname | `instance-xxx.database...` |
| `PGUSER` | Lakebase username | `user@domain.com` |
| `PGDATABASE` | Lakebase database name | `databricks_postgres` |

## Troubleshooting

- **"uv: command not found"**: Install uv with the curl command above, then restart your shell
- **"nvm: command not found"**: Install nvm, then `source ~/.bashrc` or `source ~/.zshrc`
- **OAuth errors**: Run `databricks auth login` and select your workspace
- **Lakebase connection fails**: Verify the instance name in `.env` and check workspace permissions
