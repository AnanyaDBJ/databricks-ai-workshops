# Agent Memory System

Configure and use the long-term memory system for persistent user preferences and conversation history.

## Memory Architecture

The memory system is implemented in `agent_server/utils_memory.py` and uses:
- **Lakebase (PostgreSQL)** for persistent storage
- **databricks-gte-large-en** embeddings (1024 dims) for semantic search
- **AsyncDatabricksStore** for async read/write operations
- Per-user namespacing for data isolation

## Available Memory Tools

### User Memory Tools

| Tool | Purpose | When Used |
|---|---|---|
| `get_user_memory(query)` | Semantic search on saved memories | "What are my preferences?" |
| `save_user_memory(content)` | Persist user info/preferences | User shares "I'm vegetarian" |
| `delete_user_memory(memory_id)` | Remove a specific memory | "Forget my address" |

### Task Summary Tools

| Tool | Purpose | When Used |
|---|---|---|
| `save_task_summary(title, summary)` | Record completed task | After answering a question (silent) |
| `search_task_history(query)` | Find past tasks | "What did you help me with?" |

### Conversation Summary Tools

| Tool | Purpose | When Used |
|---|---|---|
| `save_conversation_summary(summary, topics)` | Record conversation end-state | User says goodbye (silent) |
| `search_past_conversations(query)` | Find past interactions | "What have we talked about?" |

## How It Works

1. **User sends a message** with `context.user_id`
2. **Agent checks memories** at conversation start via `get_user_memory`
3. **Agent saves preferences** when user shares personal info
4. **Agent saves task summaries** silently after completing discrete tasks
5. **Agent saves conversation summary** silently when user says goodbye

## Enabling Memory

Memory requires a `user_id` in the request context:

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{"role": "user", "content": "I prefer organic produce"}],
    "context": {"user_id": "user@example.com"}
  }'
```

Without `user_id`, memory tools are disabled and the agent logs a warning.

## Memory Storage Details

- Memories stored in Lakebase `public.store` and `public.store_vectors` tables
- Each memory has an embedding for semantic similarity search
- Memories are namespaced: `("user_memories", user_id)` for user prefs
- Task summaries namespaced: `("task_summaries", user_id)`
- Conversation summaries: `("conversation_summaries", user_id)`

## Customizing Memory

### Change Embedding Model

Edit `agent_server/agent.py`:
```python
EMBEDDING_ENDPOINT = "databricks-gte-large-en"
EMBEDDING_DIMS = 1024
```

### Add New Memory Categories

Add new tools in `agent_server/utils_memory.py` following the pattern of existing tools. Each tool needs:
1. A `@tool` decorated function
2. Access to the `BaseStore` via `RunnableConfig`
3. A unique namespace tuple

### Update System Prompt

When changing memory behavior, update the memory section in `SYSTEM_PROMPT` (`agent_server/agent.py`) so the LLM knows the new capabilities.
