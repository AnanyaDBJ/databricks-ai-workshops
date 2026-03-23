import logging
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Optional, Sequence, TypedDict

import mlflow
from databricks.sdk import WorkspaceClient
from databricks_langchain import (
    AsyncCheckpointSaver,
    AsyncDatabricksStore,
    ChatDatabricks,
    DatabricksMCPServer,
    DatabricksMultiServerMCPClient,
)
from fastapi import HTTPException
from langchain.agents import create_agent
from langchain_core.messages import AnyMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.store.base import BaseStore
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    to_chat_completions_input,
)
from typing_extensions import Annotated

from agent_server.utils import (
    _get_or_create_thread_id,
    get_databricks_host_from_env,
    get_session_id,
    get_user_workspace_client,
    process_agent_astream_events,
)
from agent_server.utils_memory import (
    get_lakebase_access_error_message,
    get_user_id,
    memory_tools,
    resolve_lakebase_instance_name,
)

logger = logging.getLogger(__name__)
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
mlflow.langchain.autolog()
sp_workspace_client = WorkspaceClient()


@tool
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.now().isoformat()


############################################
# Configuration
############################################
LLM_ENDPOINT_NAME = "databricks-claude-sonnet-4-5"
_LAKEBASE_INSTANCE_NAME_RAW = os.getenv("LAKEBASE_INSTANCE_NAME") or None
EMBEDDING_ENDPOINT = "databricks-gte-large-en"
EMBEDDING_DIMS = 1024
LAKEBASE_AUTOSCALING_PROJECT = os.getenv("LAKEBASE_AUTOSCALING_PROJECT") or None
LAKEBASE_AUTOSCALING_BRANCH = os.getenv("LAKEBASE_AUTOSCALING_BRANCH") or None

# TODO: Set via GENIE_SPACE_ID env var or replace default here
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "")
# TODO: Set via VECTOR_SEARCH_INDEX env var or replace default here
# Format: <catalog>/<schema>/<index-name>
VECTOR_SEARCH_INDEX = os.getenv("VECTOR_SEARCH_INDEX", "")

############################################

_has_autoscaling = LAKEBASE_AUTOSCALING_PROJECT and LAKEBASE_AUTOSCALING_BRANCH
if not _LAKEBASE_INSTANCE_NAME_RAW and not _has_autoscaling:
    raise ValueError(
        "Lakebase configuration is required but not set. "
        "Please set one of the following in your environment:\n"
        "  Option 1 (provisioned): LAKEBASE_INSTANCE_NAME=<your-instance-name>\n"
        "  Option 2 (autoscaling): LAKEBASE_AUTOSCALING_PROJECT=<project> and LAKEBASE_AUTOSCALING_BRANCH=<branch>\n"
    )

# Resolve hostname to instance name if needed (if given hostname of lakebase instead of name)
LAKEBASE_INSTANCE_NAME = resolve_lakebase_instance_name(_LAKEBASE_INSTANCE_NAME_RAW) if _LAKEBASE_INSTANCE_NAME_RAW else None


class StatefulAgentState(TypedDict, total=False):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    custom_inputs: dict[str, Any]
    custom_outputs: dict[str, Any]


SYSTEM_PROMPT = """You are a friendly and knowledgeable FreshMart grocery shopping assistant. Your role is to help customers with their grocery shopping needs, answer questions about products and purchases, and provide information about store policies.

## Your Capabilities

### Structured Data Queries (via Genie tool)
You can look up real-time information about:
- **Customer accounts:** Membership tier, purchase history, preferences
- **Products:** Pricing, stock availability, categories, aisle locations
- **Transactions:** Past orders, payment methods, order status
- **Stores:** Locations, hours, contact information
- **Payment history:** Payment methods on file

When a customer asks about their purchases, account details, product availability, or transaction history, use the Genie tool to query the data. Always be specific with queries — include customer IDs, product names, or date ranges when available.

### Policy & Procedure Lookups (via Vector Search tool)
You can search store policy documents covering:
- **Returns & refunds** — Return windows, perishable item rules, no-receipt returns
- **Membership & loyalty program** — Tier benefits (Bronze/Silver/Gold/Platinum), points, rewards
- **Delivery & pickup** — Same-day delivery, curbside pickup, fees by tier
- **Product safety & recalls** — Active recalls, how to return recalled items
- **Privacy policy** — Data collection, opt-out options, data deletion
- **Customer service** — Contact channels, escalation process, resolution times
- **Store operations** — Hours, holidays, price matching, payment methods

When a customer asks about policies, use the vector search tool to find the relevant policy details. Quote specific numbers (return windows, fees, point values) rather than being vague.

### Memory (Long-Term)
You can remember information about customers across conversations:
- Use **get_user_memory** to recall previously saved preferences, dietary restrictions, or other personal details
- Use **save_user_memory** to remember things customers share (e.g., "I'm vegetarian", "I prefer organic produce", "My usual store is the Hawthorne location")
- Use **delete_user_memory** when a customer asks you to forget something

Always check for relevant memories at the start of a conversation to provide personalized responses.

### Task & Conversation Summaries (Long-Term)
You can also remember what tasks you helped with and what conversations you had:

**Task summaries** — After completing a discrete task (e.g., answering a product question, looking up an order, explaining a policy):
- Call **save_task_summary** silently (do not mention it to the user) with a brief title and summary of what was accomplished
- Use your judgment on what constitutes a "completed task" — it could be answering a question, resolving an issue, or providing a recommendation

**Conversation summaries** — When the user signals the conversation is ending (e.g., "thank you", "bye", "that's all", "goodbye"):
- Call **save_conversation_summary** silently BEFORE your farewell response, with an overall summary and list of topics discussed
- Do not tell the user you are saving this

**Searching past history** — Route queries to the right tool:
- Preference/personal info queries (e.g., "what are my preferences?", "am I vegetarian?") → **get_user_memory**
- Specific past task queries (e.g., "what did you help me find last time?", "did I ask about returns?") → **search_task_history**
- Broad conversation history queries (e.g., "what have we talked about?", "summarize our past interactions") → **search_past_conversations**
- If unsure which applies, search both **search_task_history** and **search_past_conversations**

## Guidelines
- Be warm, helpful, and conversational — you're a friendly grocery assistant
- When providing product recommendations, consider the customer's dietary preferences and past purchases
- If asked about placing orders, making returns, or requesting refunds, explain the process but clarify that those actions need to be completed in-store, via the app, or through customer service
- For questions about out-of-stock items, check the product data and suggest alternatives in the same category
- Always mention relevant loyalty benefits when applicable (e.g., "As a Gold member, you get free delivery on orders over $50!")
- If you don't have enough information to answer, ask clarifying questions rather than guessing"""


def init_mcp_client(workspace_client: WorkspaceClient) -> DatabricksMultiServerMCPClient:
    host_name = get_databricks_host_from_env()
    return DatabricksMultiServerMCPClient(
        [
            DatabricksMCPServer(
                name="system-ai",
                url=f"{host_name}/api/2.0/mcp/functions/system/ai",
                workspace_client=workspace_client,
            ),
            DatabricksMCPServer(
                name="retail-grocery-genie",
                url=f"{host_name}/api/2.0/mcp/genie/{GENIE_SPACE_ID}",
                workspace_client=workspace_client,
            ),
            DatabricksMCPServer(
                name="retail-policy-docs",
                url=f"{host_name}/api/2.0/mcp/vector-search/{VECTOR_SEARCH_INDEX}",
                workspace_client=workspace_client,
            ),
        ]
    )


async def init_agent(
    store: BaseStore,
    workspace_client: Optional[WorkspaceClient] = None,
    checkpointer: Optional[Any] = None,
):
    mcp_client = init_mcp_client(workspace_client or sp_workspace_client)
    tools = [get_current_time] + memory_tools() + await mcp_client.get_tools()

    return create_agent(
        model=ChatDatabricks(endpoint=LLM_ENDPOINT_NAME),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        store=store,
        checkpointer=checkpointer,
        state_schema=StatefulAgentState,
    )


@invoke()
async def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    thread_id = _get_or_create_thread_id(request)
    request.custom_inputs = dict(request.custom_inputs or {})
    request.custom_inputs["thread_id"] = thread_id

    outputs = [
        event.item
        async for event in stream_handler(request)
        if event.type == "response.output_item.done"
    ]

    user_id = get_user_id(request)
    custom_outputs = {"thread_id": thread_id}
    if user_id:
        custom_outputs["user_id"] = user_id
    return ResponsesAgentResponse(output=outputs, custom_outputs=custom_outputs)


@stream()
async def stream_handler(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    thread_id = _get_or_create_thread_id(request)
    if session_id := get_session_id(request):
        mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})
    mlflow.update_current_trace(metadata={"mlflow.trace.session": thread_id})

    user_id = get_user_id(request)

    if not user_id:
        logger.warning("No user_id provided - memory features will not be available")

    input_state: dict[str, Any] = {
        "messages": to_chat_completions_input([i.model_dump() for i in request.input]),
        "custom_inputs": dict(request.custom_inputs or {}),
    }

    try:
        async with AsyncCheckpointSaver(
            instance_name=LAKEBASE_INSTANCE_NAME,
            project=LAKEBASE_AUTOSCALING_PROJECT,
            branch=LAKEBASE_AUTOSCALING_BRANCH,
        ) as checkpointer:
            await checkpointer.setup()
            async with AsyncDatabricksStore(
                instance_name=LAKEBASE_INSTANCE_NAME,
                project=LAKEBASE_AUTOSCALING_PROJECT,
                branch=LAKEBASE_AUTOSCALING_BRANCH,
                embedding_endpoint=EMBEDDING_ENDPOINT,
                embedding_dims=EMBEDDING_DIMS,
            ) as store:
                await store.setup()
                config: dict[str, Any] = {"configurable": {"thread_id": thread_id, "store": store}}
                if user_id:
                    config["configurable"]["user_id"] = user_id

                agent = await init_agent(
                    workspace_client=sp_workspace_client,
                    store=store,
                    checkpointer=checkpointer,
                )
                async for event in process_agent_astream_events(
                    agent.astream(input_state, config, stream_mode=["updates", "messages"])
                ):
                    yield event
    except Exception as e:
        error_msg = str(e).lower()
        # Check for Lakebase access/connection errors
        if any(keyword in error_msg for keyword in ["permission"]):
            logger.error(f"Lakebase access error: {e}")
            lakebase_desc = LAKEBASE_INSTANCE_NAME or f"{LAKEBASE_AUTOSCALING_PROJECT}/{LAKEBASE_AUTOSCALING_BRANCH}"
            raise HTTPException(
                status_code=503, detail=get_lakebase_access_error_message(lakebase_desc)
            ) from e
        raise
