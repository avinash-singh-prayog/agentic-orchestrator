# Serviceability Agent API Documentation

The Serviceability Agent is a worker agent that handles serviceability checks, rate quotes, and shipment booking. It can be accessed directly via HTTP or through SLIM Transporter.

## Base URL

| Environment | URL |
|------------|-----|
| Local (Docker) | `http://localhost:9003` |
| Local (uvicorn) | `http://localhost:8000` |
| Container Network | `http://serviceability-agent:8000` |

---

## Endpoints

### 1. Run Agent

Execute the serviceability agent with a natural language prompt. The agent uses LangGraph to parse the request, check serviceability, and generate a response.

**Endpoint:** `POST /serviceability-agent/v1/agent/run`

**Request Body:**
```json
{
  "prompt": "string"
}
```

**Response:**
```json
{
  "response": "string",
  "label": {
    "tracking_number": "string",
    "label_url": "string",
    "carrier": "string"
  } | null,
  "error": "string" | null
}
```

**Example - Check Rates:**
```bash
curl -X POST http://localhost:9003/serviceability-agent/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Get shipping rates for 5kg from Mumbai 400001 to Delhi 110001"
  }'
```

**Example Response:**
```json
{
  "response": "Here are the shipping rates for a 5kg package from Mumbai to Delhi:\n1. Aramex Express - ₹450\n2. FedEx Priority - ₹520",
  "label": null,
  "error": null
}
```

---

### 2. Check Serviceability

Check serviceability across all enabled carriers for a given route. This is a direct API call to the integrated carrier services.

**Endpoint:** `POST /serviceability-agent/v1/serviceability`

**Request Body:**
```json
{
  "source_location": {
    "postal_code": "string",
    "country_code": "string"
  },
  "destination_location": {
    "postal_code": "string",
    "country_code": "string"
  },
  "packages": [
    {
      "weight": { "value": 1.0, "unit": "kg" },
      "dimensions": { "length": 10, "width": 10, "height": 10, "unit": "cm" }
    }
  ]
}
```

**Response:**
```json
{
  "source_postal_code": "string",
  "destination_postal_code": "string",
  "source_country_code": "string",
  "destination_country_code": "string",
  "flow": "domestic" | "international",
  "carriers": [...],
  "serviceable_count": 0,
  "total_carriers": 0
}
```

**Example - International Shipment:**
```bash
curl -X POST http://localhost:9003/serviceability-agent/v1/serviceability \
  -H "Content-Type: application/json" \
  -d '{
    "source_location": {
      "postal_code": "193501",
      "country_code": "IN"
    },
    "destination_location": {
      "postal_code": "10001",
      "country_code": "US"
    }
  }'
```

**Example Response:**
```json
{
  "source_postal_code": "193501",
  "destination_postal_code": "10001",
  "source_country_code": "IN",
  "destination_country_code": "US",
  "flow": "international",
  "carriers": [
    {
      "partner_code": "shipcube",
      "partner_name": "ShipCube",
      "is_serviceable": true,
      "services": [
        {
          "service_code": "Standard",
          "service_name": "weight_based_rates",
          "rate": { "currency": "INR", "amount": 380.0 }
        }
      ]
    },
    {
      "partner_code": "aramex",
      "partner_name": "Aramex",
      "is_serviceable": true,
      "services": [
        {
          "service_code": "PDX",
          "service_name": "Priority Document Express",
          "tat_days": 2,
          "rate": { "currency": "INR", "amount": 5066.92 }
        }
      ]
    },
    {
      "partner_code": "fedex",
      "partner_name": "FedEx",
      "is_serviceable": true,
      "services": [
        {
          "service_code": "INTERNATIONAL_ECONOMY",
          "service_name": "FedEx International Economy®",
          "tat_days": 5,
          "rate": { "currency": "USD", "amount": 264.6 }
        }
      ]
    }
  ],
  "serviceable_count": 3,
  "total_carriers": 3
}
```

**Example - Domestic Shipment:**
```bash
curl -X POST http://localhost:9003/serviceability-agent/v1/serviceability \
  -H "Content-Type: application/json" \
  -d '{
    "source_location": {
      "postal_code": "400001",
      "country_code": "IN"
    },
    "destination_location": {
      "postal_code": "110001",
      "country_code": "IN"
    }
  }'
```

---

### 3. Health Check

Check if the serviceability agent is running and list available carriers.

**Endpoint:** `GET /serviceability-agent/v1/health`

**Response:**
```json
{
  "status": "healthy",
  "carriers": ["aramex", "fedex", "shipcube"]
}
```

**Example:**
```bash
curl http://localhost:9003/serviceability-agent/v1/health
```

---

## Running Modes

The Serviceability Agent supports two running modes:

### 1. HTTP Mode (FastAPI)
Direct HTTP access for testing and development.

```bash
# Local
uv run --package serviceability-agent uvicorn serviceability_agent.app.main:app --host 0.0.0.0 --port 8000

# Docker
docker compose up serviceability-agent  # Without SLIM mode
```

### 2. SLIM Mode (A2A Protocol)
Registers with SLIM Gateway for inter-agent communication.

```bash
# Docker (default)
docker compose up serviceability-agent  # Uses "slim" argument

# Direct
python -m serviceability_agent.app.main slim
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Serviceability Agent                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ HTTP API    │    │  LangGraph   │    │ Serviceability│  │
│  │ (FastAPI)   │───▶│  Workflow    │───▶│     Tool      │  │
│  └─────────────┘    └──────────────┘    └───────┬───────┘  │
│                                                  │          │
│  ┌─────────────┐                                 ▼          │
│  │ SLIM Server │    ┌──────────────────────────────────┐   │
│  │ (A2A)       │    │     External Serviceability API   │   │
│  └─────────────┘    │     (Port 9022)                   │   │
│                     │  ┌─────────┬────────┬──────────┐  │   │
│                     │  │ FedEx   │ Aramex │ ShipCube │  │   │
│                     │  └─────────┴────────┴──────────┘  │   │
│                     └──────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICEABILITY_AGENT_LLM` | LLM model to use | `openrouter/openai/gpt-4o-mini` |
| `OPENROUTER_API_KEY` | API key for OpenRouter | Required |
| `SLIM_ENDPOINT` | SLIM Gateway URL | `http://orchestrator-slim:46357` |
| `SERVICEABILITY_API_URL` | External serviceability API | `http://host.docker.internal:9022/serviceability/v3/check` |
| `OTLP_HTTP_ENDPOINT` | OpenTelemetry endpoint | `http://otel-collector:4318` |
