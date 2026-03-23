# Migrate from Model Serving to Databricks Apps

Guide for migrating an agent from Databricks Model Serving to Databricks Apps.

## Key Differences

| Aspect | Model Serving | Databricks Apps |
|---|---|---|
| **Interface** | ChatCompletions API | Responses API (OpenAI compatible) |
| **Auth** | PAT or OAuth | OAuth only |
| **UI** | Separate deployment | Built-in chat UI |
| **Resources** | Via serving endpoint config | Via app resources + service principal |
| **Scaling** | Auto-scaled containers | App runtime |
| **Framework** | MLflow pyfunc | MLflow AgentServer |

## Migration Steps

### 1. Convert Agent Interface

**Before (Model Serving / ChatCompletions)**:
```python
class MyAgent(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input):
        # ChatCompletions format
        messages = model_input["messages"]
        return {"choices": [{"message": {"content": response}}]}
```

**After (Databricks Apps / ResponsesAgent)**:
```python
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse

@invoke()
async def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    # Responses API format
    messages = to_chat_completions_input([i.model_dump() for i in request.input])
    # ... agent logic ...
    return ResponsesAgentResponse(output=outputs)

@stream()
async def stream_handler(request: ResponsesAgentRequest):
    # Streaming via async generator
    async for event in process_events(...):
        yield event
```

### 2. Update Server Startup

**Before**: MLflow model serving with `mlflow models serve`

**After** (`agent_server/start_server.py`):
```python
from mlflow.genai.agent_server import AgentServer
server = AgentServer(agent_type="ResponsesAgent")
```

### 3. Configure App Resources

Create `app.yaml` and `databricks.yml` with resource declarations for:
- MLflow experiment
- Genie spaces
- Vector Search indexes
- Lakebase instances

### 4. Handle Authentication

- Replace PAT-based auth with OAuth
- Use `get_user_workspace_client()` for OBO (on-behalf-of) user auth
- Configure app service principal permissions for all resources

### 5. Add the Chat UI

The `e2e-chatbot-app-next/` directory provides a built-in React chat UI that automatically connects to the agent server.

### 6. Deploy

```bash
databricks apps create my-agent-app
databricks sync . "/Users/$DATABRICKS_USERNAME/my-agent-app"
databricks apps deploy my-agent-app --source-code-path /Workspace/Users/$DATABRICKS_USERNAME/my-agent-app
```

## Testing the Migration

```bash
# Start locally
uv run start-app

# Test API compatibility
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "test"}]}'
```
