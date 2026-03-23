# Run the Agent Locally

Start the agent server and chat UI for local development and testing.

## Quick Start

```bash
uv run start-app
```

This starts both:
- **Agent server** (FastAPI/MLflow) on port 8000
- **Chat UI** (React/Vite) on port 3000

## Server-Only Mode

```bash
uv run start-app --no-ui
# or
uv run start-server
```

### Server Options

```bash
uv run start-server --reload    # Hot-reload on code changes
uv run start-server --port 8001 # Custom port
uv run start-server --workers 4 # Multiple workers
```

## Testing via API

### Streaming

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "hi"}], "stream": true}'
```

### Non-Streaming

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "What are your return policies?"}]}'
```

### With User Context (enables memory)

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{"role": "user", "content": "Remember I prefer organic"}],
    "context": {"user_id": "test@example.com"}
  }'
```

## Running Evaluations

```bash
uv run agent-evaluate
```

Uses MLflow ConversationSimulator with 9 scorers. Results appear in your MLflow experiment.

## Environment Requirements

Ensure `.env` is configured with all required variables. See `.env.example` for the template.

## Troubleshooting

- **Port already in use**: Kill the existing process or use `--port` flag
- **"Lakebase configuration is required"**: Set `LAKEBASE_INSTANCE_NAME` in `.env`
- **Frontend not loading**: Check that Node.js 20 is active (`nvm use 20`)
- **MCP tool errors**: Verify `GENIE_SPACE_ID` and `VECTOR_SEARCH_INDEX` in `.env`
