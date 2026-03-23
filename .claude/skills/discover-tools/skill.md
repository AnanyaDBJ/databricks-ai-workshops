# Discover Available Databricks Tools

Find and list tools available in your Databricks workspace that can be added to the agent.

## Run Discovery

```bash
uv run discover-tools
```

This scans for:
- **Unity Catalog Functions** — Custom SQL/Python functions registered as UC tools
- **Vector Search Indexes** — RAG-enabled document indexes for retrieval
- **Genie Spaces** — Natural language to SQL interfaces over curated datasets
- **Custom MCP Servers** — Databricks Apps with names prefixed `mcp-*`
- **UC Tables** — Data sources available in Unity Catalog

## Script Location

`scripts/discover_tools.py`

## Output Format

The script outputs structured JSON with discovered tools grouped by type:

```json
{
  "uc_functions": [...],
  "vector_search_indexes": [...],
  "genie_spaces": [...],
  "mcp_servers": [...],
  "uc_tables": [...]
}
```

## Using Discovered Tools

After discovery, add tools to your agent by modifying `agent_server/agent.py`:

### Add a Genie Space
```python
DatabricksMCPServer(
    name="my-genie-space",
    url=f"{host_name}/api/2.0/mcp/genie/{GENIE_SPACE_ID}",
    workspace_client=workspace_client,
)
```

### Add a Vector Search Index
```python
DatabricksMCPServer(
    name="my-docs",
    url=f"{host_name}/api/2.0/mcp/vector-search/{VECTOR_SEARCH_INDEX}",
    workspace_client=workspace_client,
)
```

### Add a UC Function
```python
DatabricksMCPServer(
    name="my-function",
    url=f"{host_name}/api/2.0/mcp/functions/{catalog}/{schema}",
    workspace_client=workspace_client,
)
```
