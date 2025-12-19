# Supervisor Agent API Documentation

The Supervisor Agent is the orchestration layer that receives user requests and delegates to worker agents (like the Carrier Agent) via SLIM Transporter.

## Base URL

| Environment | URL |
|------------|-----|
| Local (Docker) | `http://localhost:9004` |
| Container Network | `http://supervisor-agent:8000` |

---

## Endpoints

### 1. Run Agent

Execute the supervisor agent with a natural language prompt. The agent will analyze the request and delegate to appropriate worker agents.

**Endpoint:** `POST /supervisor-agent/supervisor/v1/agent/run`

**Request Body:**
```json
{
  "prompt": "string"
}
```

**Response:**
```json
{
  "response": "string"
}
```

**Example - Check Shipping Rates:**
```bash
curl -X POST http://localhost:9004/supervisor-agent/supervisor/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Check shipping rates for 5kg from 193501 India to 10001 US"
  }'
```

**Example Response:**
```json
{
  "response": "Here are the shipping rates for a 5kg package from 193501, India to 10001, US:\n\n1. **ShipCube** - Standard: ₹742.00\n2. **Aramex** - Priority Parcel Express: ₹17,451.02\n3. **FedEx** - FedEx International Economy®: $435.95\n..."
}
```

**Example - Check Serviceability:**
```bash
curl -X POST http://localhost:9004/supervisor-agent/supervisor/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Can you ship from Mumbai 400001 to Delhi 110001?"
  }'
```

---

### 2. Health Check

Check if the supervisor agent is running and healthy.

**Endpoint:** `GET /supervisor-agent/health`

**Response:**
```json
{
  "status": "ok"
}
```

**Example:**
```bash
curl http://localhost:9004/supervisor-agent/health
```

---

## Architecture

The Supervisor Agent:
1. Receives natural language requests via HTTP
2. Uses LangGraph workflow with LLM to determine intent
3. Delegates to worker agents via SLIM Transporter (A2A Protocol)
4. Aggregates responses and returns to user

```
┌─────────────────┐     ┌──────────────┐     ┌────────────────┐
│  HTTP Request   │────▶│  Supervisor  │────▶│  SLIM Gateway  │
│  (Port 9004)    │     │    Agent     │     │  (Port 46357)  │
└─────────────────┘     └──────────────┘     └───────┬────────┘
                                                     │
                                                     ▼
                                             ┌────────────────┐
                                             │ Carrier Agent  │
                                             │ (Worker)       │
                                             └────────────────┘
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPERVISOR_LLM` | LLM model to use | `openrouter/openai/gpt-4o-mini` |
| `OPENROUTER_API_KEY` | API key for OpenRouter | Required |
| `SLIM_ENDPOINT` | SLIM Gateway URL | `http://orchestrator-slim:46357` |
| `OTLP_HTTP_ENDPOINT` | OpenTelemetry endpoint | `http://otel-collector:4318` |
