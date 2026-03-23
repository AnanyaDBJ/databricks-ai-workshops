# Add Tools to the Agent

Add new MCP tools, UC functions, or custom tools to the agent.

## How Tools Work

The agent uses MCP (Model Context Protocol) to connect to Databricks tool servers. Tools are defined in `agent_server/agent.py` inside the `init_mcp_client()` function.

## Adding an MCP Tool

Edit `agent_server/agent.py` and add a new `DatabricksMCPServer` entry:

```python
def init_mcp_client(workspace_client: WorkspaceClient) -> DatabricksMultiServerMCPClient:
    host_name = get_databricks_host_from_env()
    return DatabricksMultiServerMCPClient(
        [
            # ... existing servers ...

            # Add your new server here:
            DatabricksMCPServer(
                name="my-tool-name",
                url=f"{host_name}/api/2.0/mcp/...",
                workspace_client=workspace_client,
            ),
        ]
    )
```

### MCP URL Patterns

| Tool Type | URL Pattern |
|---|---|
| Genie Space | `/api/2.0/mcp/genie/{space_id}` |
| Vector Search | `/api/2.0/mcp/vector-search/{catalog}/{schema}/{index}` |
| UC Functions | `/api/2.0/mcp/functions/{catalog}/{schema}` |
| System AI | `/api/2.0/mcp/functions/system/ai` |

## Adding a Custom LangChain Tool

Add a Python function with the `@tool` decorator in `agent_server/agent.py`:

```python
from langchain_core.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """Description of what this tool does. The LLM reads this to decide when to use it."""
    # Your implementation here
    return result
```

Then include it in the tools list inside `init_agent()`:

```python
tools = [get_current_time, my_custom_tool] + memory_tools() + await mcp_client.get_tools()
```

## Adding Environment Variables for New Tools

1. Add to `.env.example`:
   ```
   MY_NEW_TOOL_ID=
   ```

2. Add to `app.yaml` (for deployment):
   ```yaml
   - name: MY_NEW_TOOL_ID
     value: "<your-value>"
   ```

3. Add to `databricks.yml` (for bundle deployment):
   ```yaml
   env:
     - name: MY_NEW_TOOL_ID
       value: "<your-value>"
   ```

## Discovering Available Tools

Run the discovery script to find tools in your workspace:

```bash
uv run discover-tools
```

## Updating the System Prompt

After adding a tool, update the `SYSTEM_PROMPT` in `agent_server/agent.py` to describe the new capability so the LLM knows when and how to use it.
