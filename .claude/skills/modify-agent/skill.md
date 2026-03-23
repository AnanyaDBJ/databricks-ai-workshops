# Modify the Agent

Customize the agent's behavior, tools, LLM, and system prompt.

## Key Files

| File | Purpose |
|---|---|
| `agent_server/agent.py` | Core agent logic — LLM, tools, system prompt, handlers |
| `agent_server/utils_memory.py` | Memory tools (7 tools for user preferences, tasks, conversations) |
| `agent_server/utils.py` | Auth helpers, thread management, streaming |
| `agent_server/evaluate_agent.py` | Evaluation dataset and scorers |

## Common Modifications

### Change the LLM

Edit `agent_server/agent.py`:

```python
LLM_ENDPOINT_NAME = "databricks-claude-sonnet-4-5"  # Change to any FMAPI endpoint
```

### Edit the System Prompt

The `SYSTEM_PROMPT` variable in `agent_server/agent.py` defines the agent's personality and capabilities. Modify it to:
- Change the persona (e.g., from grocery assistant to tech support)
- Add/remove capability descriptions
- Update guidelines for tool usage

### Add Custom Tools

See the `add-tools` skill for detailed instructions on adding MCP servers and custom LangChain tools.

### Modify Memory Behavior

Edit `agent_server/utils_memory.py` to:
- Change how memories are stored/retrieved
- Add new memory categories
- Adjust embedding model (`EMBEDDING_ENDPOINT`)
- Change the Lakebase schema

### Customize Evaluation

Edit `agent_server/evaluate_agent.py`:

```python
test_cases = [
    {
        "goal": "Your test scenario goal",
        "persona": "Description of the simulated user",
        "simulation_guidelines": ["Specific behavior instructions"],
    },
]
```

Available scorers: `Completeness`, `ConversationalSafety`, `ConversationCompleteness`, `Fluency`, `KnowledgeRetention`, `RelevanceToQuery`, `Safety`, `ToolCallCorrectness`, `UserFrustration`

### Add Python Dependencies

```bash
uv add <package_name>
```

### Add Additional Server Routes

Edit `agent_server/start_server.py` to add custom FastAPI routes (e.g., `/metrics`, `/health`).

## Agent State

The agent uses `StatefulAgentState` (TypedDict) with:
- `messages`: Conversation history (managed by LangGraph)
- `custom_inputs`: Additional request context (thread_id, user_id)
- `custom_outputs`: Response metadata

## Testing Changes

After making changes:

```bash
# Test locally
uv run start-app

# Run evaluations
uv run agent-evaluate
```
