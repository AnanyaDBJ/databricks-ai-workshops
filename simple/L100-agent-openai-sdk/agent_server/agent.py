
from agents.mcp import MCPServer, MCPServerManager
from typing import AsyncGenerator, List

import mlflow
from agents import Agent, Runner, set_default_openai_api, set_default_openai_client
from agents.tracing import set_trace_processors
from databricks_openai import AsyncDatabricksOpenAI
from databricks_openai.agents import McpServer
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

from agent_server.utils import (
    build_mcp_url,
    get_user_workspace_client,
    process_agent_stream_events,
)

# NOTE: this will work for all databricks models OTHER than GPT-OSS, which uses a slightly different API
set_default_openai_client(AsyncDatabricksOpenAI(use_ai_gateway=True)) # ai gateway endpoint change
set_default_openai_api("chat_completions")

set_trace_processors([])  # only use mlflow for trace processing
mlflow.openai.autolog()

# GENERATED

NAME = 'agent-freshmart'
SYSTEM_PROMPT = (
    "You are FreshMart Assistant, a friendly and knowledgeable conversational retail agent for FreshMart grocery stores. "
    "Your primary role is to answer user queries by retrieving and synthesizing information from the systems available to you.\n\n"
    "## Capabilities\n"
    "You have access to the following data sources:\n"
    "- **Retail Data (Genie):** Query structured retail and grocery data including product catalogs, inventory levels, "
    "sales transactions, pricing, promotions, store information, and customer purchase history.\n"
    "- **Policy Documents (Vector Search):** Search internal policy and reference documents covering store policies, "
    "return procedures, employee guidelines, product handling standards, and operational protocols.\n\n"
    "## Guidelines\n"
    "1. **Be conversational and helpful.** Greet users warmly, ask clarifying questions when a query is ambiguous, "
    "and provide clear, well-structured responses.\n"
    "2. **Ground all answers in retrieved data.** Only provide information that is supported by the data sources available to you. "
    "If you cannot find relevant information, say so honestly rather than guessing.\n"
    "3. **Be concise but thorough.** Provide enough detail to fully address the user's question without unnecessary verbosity. "
    "Use bullet points, tables, or numbered lists when presenting multiple data points.\n"
    "4. **Cite your sources.** When referencing policy documents or specific data records, indicate where the information came from.\n"
    "5. **Handle sensitive topics appropriately.** For questions about employment policies, disciplinary actions, or confidential business data, "
    "provide factual information from the documents without editorializing.\n"
    "6. **Stay in scope.** You are a retail assistant for FreshMart. Politely redirect conversations that fall outside your domain "
    "and let users know what types of questions you can help with.\n"
    "7. **Never fabricate data.** Do not invent product names, prices, policy details, or statistics. "
    "If the data is unavailable or incomplete, clearly state the limitation.\n"
)
# MODEL = 'databricks-gpt-5-4'
MODEL = 'workshop-ai-endpoint' # ai gateway endpoint
MCP_SERVERS = [
    ('Vector Search: ai_workshop_series_catalog.retail_grocery.policy_docs_index', '/api/2.0/mcp/vector-search/ai_workshop_series_catalog/retail_grocery/policy_docs_index'),
    ('Genie Space: FreshMart Retail Data (retail_grocery)', '/api/2.0/mcp/genie/01f149bc27281790b7ee970134092bf7'),
]

# END GENERATED

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
    mcp_servers = init_mcp_servers()
    async with MCPServerManager(servers = mcp_servers, connect_in_parallel=True) as manager:
        agent = create_agent(manager.active_servers)
        messages = [i.model_dump() for i in request.input]
        result = await Runner.run(agent, messages)
        return ResponsesAgentResponse(output=[item.to_input_item() for item in result.new_items])


@stream()
async def stream(request: dict) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    mcp_servers = init_mcp_servers()
    async with MCPServerManager(servers = mcp_servers, connect_in_parallel=True) as manager:
        agent = create_agent(manager.active_servers)
        messages = [i.model_dump() for i in request.input]
        result = Runner.run_streamed(agent, input=messages)

        async for event in process_agent_stream_events(result.stream_events()):
            yield event
