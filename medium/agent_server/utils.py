import logging
import os
from dataclasses import dataclass
from typing import AsyncGenerator, AsyncIterator, Optional
from uuid import uuid4

from agents.result import StreamEvent
from databricks.sdk import WorkspaceClient
from databricks_openai.agents.session import AsyncDatabricksSession
from mlflow.genai.agent_server import get_request_headers
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentStreamEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LakebaseConfig:
    instance_name: Optional[str]
    autoscaling_endpoint: Optional[str]
    autoscaling_project: Optional[str]
    autoscaling_branch: Optional[str]
    memory_schema: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        return bool(
            self.autoscaling_endpoint
            or (self.autoscaling_project and self.autoscaling_branch)
            or self.instance_name
        )

    @property
    def description(self) -> str:
        if self.autoscaling_endpoint:
            return f"autoscaling endpoint '{self.autoscaling_endpoint}'"
        if self.autoscaling_project:
            return f"autoscaling project '{self.autoscaling_project}' branch '{self.autoscaling_branch}'"
        if self.instance_name:
            return f"provisioned instance '{self.instance_name}'"
        return "not configured"


def _env_or_none(key: str) -> Optional[str]:
    """Return the env var, or None when it's unset or blank.

    Setup writes the unused Lakebase mode as an empty string (e.g.
    ``LAKEBASE_INSTANCE_NAME=`` when using autoscaling). An empty string is not
    None, so passing it through would make AsyncDatabricksSession think both the
    provisioned and autoscaling modes were requested and reject the combination.
    """
    value = os.environ.get(key)
    return value.strip() if value and value.strip() else None


def init_lakebase_config() -> Optional[LakebaseConfig]:
    config = LakebaseConfig(
        instance_name=_env_or_none("LAKEBASE_INSTANCE_NAME"),
        autoscaling_endpoint=_env_or_none("LAKEBASE_AUTOSCALING_ENDPOINT"),
        autoscaling_project=_env_or_none("LAKEBASE_AUTOSCALING_PROJECT"),
        autoscaling_branch=_env_or_none("LAKEBASE_AUTOSCALING_BRANCH"),
        memory_schema=os.environ.get("LAKEBASE_AGENT_MEMORY_SCHEMA", "agent_openai_memory"),
    )
    if not config.is_configured:
        logger.warning(
            "No Lakebase configuration found. Set LAKEBASE_INSTANCE_NAME or "
            "LAKEBASE_AUTOSCALING_ENDPOINT to enable short-term memory."
        )
        return None
    logger.info("Lakebase configured: %s", config.description)
    return config


def create_session(session_id: str, lakebase_config: LakebaseConfig) -> AsyncDatabricksSession:
    return AsyncDatabricksSession(
        session_id=session_id,
        instance_name=lakebase_config.instance_name,
        autoscaling_endpoint=lakebase_config.autoscaling_endpoint,
        project=lakebase_config.autoscaling_project,
        branch=lakebase_config.autoscaling_branch,
        schema=lakebase_config.memory_schema,
        create_tables=False,
    )


def get_session_id(request: ResponsesAgentRequest) -> str:
    if request.custom_inputs and isinstance(request.custom_inputs, dict):
        sid = request.custom_inputs.get("session_id")
        if sid:
            return sid
    if request.context and request.context.conversation_id:
        return request.context.conversation_id
    return str(uuid4())


async def deduplicate_input(
    request: ResponsesAgentRequest, session: AsyncDatabricksSession
) -> list[dict]:
    messages = [i.model_dump() for i in request.input]
    for msg in messages:
        if (
            msg.get("type") == "message"
            and msg.get("role") == "assistant"
            and isinstance(msg.get("content"), str)
        ):
            msg["content"] = [{"type": "output_text", "text": msg["content"], "annotations": []}]

    session_items = await session.get_items()
    if len(session_items) >= len(messages) - 1:
        return [messages[-1]]
    return messages


def get_databricks_host(workspace_client: WorkspaceClient | None = None) -> Optional[str]:
    workspace_client = workspace_client or WorkspaceClient()
    try:
        return workspace_client.config.host
    except Exception as e:
        logging.exception(f"Error getting databricks host from env: {e}")
        return None


def build_mcp_url(path: str, workspace_client: WorkspaceClient | None = None) -> str:
    if not path.startswith("/"):
        return path
    hostname = get_databricks_host(workspace_client)
    return f"{hostname}{path}"


def get_user_workspace_client() -> WorkspaceClient:
    token = get_request_headers().get("x-forwarded-access-token")
    return WorkspaceClient(token=token, auth_type="pat")


async def process_agent_stream_events(
    async_stream: AsyncIterator[StreamEvent],
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    curr_item_id = str(uuid4())
    async for event in async_stream:
        if event.type == "raw_response_event":
            event_data = event.data.model_dump()
            if event_data["type"] == "response.output_item.added":
                curr_item_id = str(uuid4())
                event_data["item"]["id"] = curr_item_id
            elif event_data.get("item") is not None and event_data["item"].get("id") is not None:
                event_data["item"]["id"] = curr_item_id
            elif event_data.get("item_id") is not None:
                event_data["item_id"] = curr_item_id
            yield event_data
        elif event.type == "run_item_stream_event" and event.item.type == "tool_call_output_item":
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=event.item.to_input_item(),
            )
