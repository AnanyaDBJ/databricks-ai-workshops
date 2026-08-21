
import logging
import os

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
    flatten_content_text,
    get_session_id,
    get_user_workspace_client,
    init_lakebase_config,
    install_reasoning_content_normalizer,
    process_agent_stream_events,
)

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Routing is env-driven so the same code works with or without AI Gateway.
# The two settings are coupled: AI Gateway routes to {host}/ai-gateway/mlflow/v1,
# where AGENT_MODEL is a gateway endpoint (often a UC path like
# catalog.schema.endpoint); without it, requests go to {host}/serving-endpoints,
# where AGENT_MODEL is a serving endpoint name like databricks-claude-opus-4-6.
USE_AI_GATEWAY = _env_flag("AGENT_USE_AI_GATEWAY")
DEFAULT_MODEL = "databricks-claude-opus-4-6"

# implement a simple change
# NOTE: this will work for all databricks models OTHER than GPT-OSS, which uses a slightly different API
openai_client = AsyncDatabricksOpenAI(use_ai_gateway=USE_AI_GATEWAY)
set_default_openai_client(openai_client)
set_default_openai_api("chat_completions")
set_trace_processors([])  # only use mlflow for trace processing
mlflow.openai.autolog()
# Reasoning models (e.g. databricks-claude-opus-5) return list-shaped content that
# the Agents SDK converter can't parse; normalize it. Install after autolog so the
# wrapper still routes through the traced create().
install_reasoning_content_normalizer(openai_client)

# GENERATED

NAME = 'my-agent'
SYSTEM_PROMPT = 'You are a helpful assistant.'
MODEL = os.environ.get('AGENT_MODEL', DEFAULT_MODEL)
MCP_SERVERS = [
    # Add your MCP servers here, e.g.:
    # ('Vector Search: <catalog>.<schema>.<index>', '/api/2.0/mcp/vector-search/<catalog>/<schema>/<index>'),
    # ('Genie Space: <name>', '/api/2.0/mcp/genie/<space-id>'),
]

# END GENERATED

logger.info("Agent model: %s (AI Gateway: %s)", MODEL, USE_AI_GATEWAY)
if USE_AI_GATEWAY and MODEL == DEFAULT_MODEL:
    logger.warning(
        "AGENT_USE_AI_GATEWAY is enabled but AGENT_MODEL is still the default "
        "serving endpoint %r. Set AGENT_MODEL to your AI Gateway endpoint.",
        DEFAULT_MODEL,
    )

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


def _convert_input(request_input):
    """Convert input items to a format the Agents SDK accepts.

    `exclude_none=True` lets assistant items match the SDK's easy-input-message
    branch, which requires keys to be exactly {content, role}. That branch routes
    through extract_all_content, which accepts 'text' but raises on 'output_text' —
    hence the rewrite.
    """
    messages = []
    for i in request_input:
        item = i.model_dump(exclude_none=True)
        flatten_content_text(item)
        if "content" in item and isinstance(item["content"], list):
            for c in item["content"]:
                if isinstance(c, dict) and c.get("type") == "output_text":
                    c["type"] = "text"
        messages.append(item)
    return messages


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
                messages = _convert_input(request.input)

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
            messages = _convert_input(request.input)

        result = Runner.run_streamed(agent, input=messages, session=session)

        async for event in process_agent_stream_events(result.stream_events()):
            yield event
