# workmate-runner

A FastAPI microservice that executes dynamic LangGraph multi-agent workflows. It receives a graph definition, agent configs, and tool resources from an external caller, builds the execution graph at runtime, and returns the output.

## How it works

1. A caller (e.g. the Workmate backend) sends a `POST /run` request with a graph payload describing nodes, edges, agents, and resources.
2. The service fetches any context documents from S3.
3. A LangGraph `StateGraph` is built dynamically from the payload — nodes are mapped to agents, edges define execution order.
4. Each node invokes an LLM (OpenAI, Anthropic, or Google) and optionally equips tools (Google Drive, Gmail) via a ReAct agent loop.
5. The final output is returned as a concatenated string of each node's response.

## Project structure

```
workmate-runner/
├── main.py                          # FastAPI app + entry point (port 8001)
├── requirements.txt
├── .env.example
│
├── api/
│   ├── routes.py                    # POST /run and GET /health handlers
│   └── schemas.py                   # Pydantic request/response models
│
├── core_engine/
│   ├── graph.py                     # Builds and executes the LangGraph StateGraph
│   ├── nodes.py                     # Node function factory (per-node LLM invocation)
│   ├── state.py                     # AgentState TypedDict
│   ├── llm.py                       # LLM factory (OpenAI / Anthropic / Google)
│   └── tools/
│       ├── registry.py              # Maps resource types to tool loaders
│       ├── google_drive.py          # Google Drive list-files tool
│       └── gmail.py                 # Gmail toolkit
│
├── services/
│   └── s3_service.py               # S3 / MinIO context retrieval
│
├── scripts/
│   └── local_auth_google.py        # One-time OAuth flow to generate token.json
│
└── tests/
    ├── test_llms.py                 # Smoke-tests each LLM provider
    └── payloads/                    # Example POST /run request bodies
        ├── test_payload.json
        ├── test_payload_s3.json
        ├── test_payload_drive.json
        └── test_payload_gmail.json
```

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure environment**
```bash
cp .env.example .env
# Fill in your API keys and S3 credentials
```

**3. (Optional) Authenticate Google tools**

Required only if using Google Drive or Gmail resources:
```bash
python scripts/local_auth_google.py
```
This opens a browser OAuth flow and saves `token.json` to the project root.

**4. Start the server**
```bash
python main.py
```
The service runs on `http://localhost:8001`.

## API

### `GET /health`
Returns `{"status": "ok"}`.

### `POST /run`
Executes a multi-agent LangGraph workflow.

**Request body**
```json
{
  "run_id": "r-12345",
  "mission_id": "m-6789",
  "s3_context_links": ["s3://my-bucket/briefing.txt"],
  "agents": [
    {
      "id": "agent-1",
      "name": "Research Analyst",
      "role": "Data Gatherer",
      "system_prompt": "You are a research analyst.",
      "model_provider": "anthropic",
      "model_name": "claude-3-haiku-20240307",
      "temperature": 0.2
    }
  ],
  "resources": [],
  "graph": {
    "nodes": [{ "id": "task-A", "agent_id": "agent-1", "instructions": "Summarise the briefing." }],
    "edges": [{ "source": "START", "target": "task-A" }, { "source": "task-A", "target": "END" }]
  }
}
```

See `tests/payloads/` for more examples including S3, Google Drive, and Gmail resource usage.

**Supported `model_provider` values:** `openai`, `anthropic`, `google`

**Supported `resource.type` values:** `google_drive`, `gmail`

## Environment variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GOOGLE_API_KEY` | Google Generative AI API key |
| `S3_ENDPOINT_URL` | S3-compatible endpoint (e.g. `http://localhost:9000` for MinIO) |
| `AWS_ACCESS_KEY_ID` | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | S3 secret key |

If a provider's API key is missing, the service falls back to `gpt-4o-mini` via OpenAI.
