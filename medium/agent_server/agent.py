
import logging

from agents.mcp import MCPServer, MCPServerManager
from typing import AsyncGenerator, List

import mlflow
from agents import Agent, Runner, set_default_openai_api, set_default_openai_client
from agents.tracing import set_trace_processors
from databricks_openai import AsyncDatabricksOpenAI
from databricks_openai.agents import McpServer
from fastapi import HTTPException
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

from agent_server.utils import (
    build_mcp_url,
    create_session,
    deduplicate_input,
    get_session_id,
    get_user_workspace_client,
    init_lakebase_config,
    process_agent_stream_events,
)

logger = logging.getLogger(__name__)

# implement a simple change
# NOTE: this will work for all databricks models OTHER than GPT-OSS, which uses a slightly different API
set_default_openai_client(AsyncDatabricksOpenAI())
set_default_openai_api("chat_completions")
set_trace_processors([])  # only use mlflow for trace processing
mlflow.openai.autolog()

# GENERATED

NAME = 'my-agent'
SYSTEM_PROMPT = 'You are a helpful assistant.'
MODEL = 'databricks-claude-opus-4-6'
MCP_SERVERS = [
    # Add your MCP servers here, e.g.:
    # ('Vector Search: <catalog>.<schema>.<index>', '/api/2.0/mcp/vector-search/<catalog>/<schema>/<index>'),
    # ('Genie Space: <name>', '/api/2.0/mcp/genie/<space-id>'),
]

# END GENERATED

lakebase_config = init_lakebase_config()

def get_mcp_user_workspace_client():
    # Uncomment the line below to enable on-behalf-of-user authentication
    # return get_user_workspace_client()
    return None

def init_mcp_servers():
    user_workspace_client = get_mcp_user_workspace_client()
    return [
        McpServer(
            name=name,
            url=build_mcp_url(url, user_workspace_client),
            workspace_client=user_workspace_client,
        )
        for (name, url) in MCP_SERVERS
    ]

def create_agent(mcp_servers: List[MCPServer]) -> Agent:
    return Agent(
        name=NAME,
        instructions=SYSTEM_PROMPT,
        model=MODEL,
        mcp_servers=mcp_servers,
    )


@invoke()
async def invoke(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    session_id = get_session_id(request)
    session = None

    if lakebase_config:
        session = create_session(session_id, lakebase_config)
        mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})

    try:
        mcp_servers = init_mcp_servers()
        async with MCPServerManager(servers=mcp_servers, connect_in_parallel=True) as manager:
            agent = create_agent(manager.active_servers)

            if session:
                messages = await deduplicate_input(request, session)
            else:
                messages = [i.model_dump() for i in request.input]

            result = await Runner.run(agent, messages, session=session)
            return ResponsesAgentResponse(
                output=[item.to_input_item() for item in result.new_items],
                custom_outputs={"session_id": session.session_id} if session else None,
            )
    except Exception as e:
        error_msg = str(e).lower()
        if any(kw in error_msg for kw in ["lakebase", "pg_hba", "postgres", "database instance"]):
            logger.error("Lakebase access error: %s", e)
            raise HTTPException(status_code=503, detail=f"Lakebase unavailable: {e}") from e
        raise


@stream()
async def stream(request: ResponsesAgentRequest) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    session_id = get_session_id(request)
    session = None

    if lakebase_config:
        session = create_session(session_id, lakebase_config)
        mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})

    mcp_servers = init_mcp_servers()
    async with MCPServerManager(servers=mcp_servers, connect_in_parallel=True) as manager:
        agent = create_agent(manager.active_servers)

        if session:
            messages = await deduplicate_input(request, session)
        else:
            messages = [i.model_dump() for i in request.input]

        result = Runner.run_streamed(agent, input=messages, session=session)

        async for event in process_agent_stream_events(result.stream_events()):
            yield event
