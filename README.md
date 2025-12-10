# Generic Logistics Orchestrator V1

A multi-agent orchestration system for logistics, built on the **AGNTCY framework** with **LangGraph** and **Python 3.14**.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Supervisor                   │
│                      (LangGraph ReAct)                       │
├─────────────────────────────────────────────────────────────┤
│                         SLIM Transport                       │
├──────────────────┬──────────────────┬───────────────────────┤
│ Serviceability   │    Rate Agent    │    Carrier Agent      │
│     Agent        │   (Parallel API) │    (HITL Support)     │
└──────────────────┴──────────────────┴───────────────────────┘
```

### Key Features

- **Multi-Agent Orchestration**: Supervisor-worker topology using LangGraph
- **SOLID-Compliant LLM Abstraction**: Vendor-neutral LLM integration via LiteLLM
- **Human-in-the-Loop (HITL)**: Approval workflow for high-value orders
- **Production-Ready Identity Service**: TBAC policy-based access control
- **OASF Compliance**: Open Agent Schema Framework for discovery

## 📁 Project Structure

```
agentic-orchestrator/
├── src/orchestrator/
│   ├── agents/
│   │   ├── supervisor/         # Orchestrator supervisor
│   │   │   ├── graph.py        # LangGraph workflow
│   │   │   ├── tools.py        # LangChain tools
│   │   │   ├── hitl.py         # HITL manager
│   │   │   └── main.py         # FastAPI server
│   │   └── workers/
│   │       ├── serviceability/ # Route validation
│   │       ├── rate_agent/     # Rate aggregation
│   │       └── carrier/        # Booking execution
│   ├── common/
│   │   ├── config.py           # Configuration
│   │   ├── factory.py          # AGNTCY factory
│   │   └── llm.py              # LLM provider factory
│   ├── interfaces/
│   │   └── llm_provider.py     # LLM abstraction
│   ├── models/
│   │   └── order.py            # Order data models
│   ├── providers/
│   │   └── litellm_adapter.py  # LiteLLM implementation
│   └── services/
│       └── identity/           # Identity service
├── config/docker/
│   ├── otel/                   # OpenTelemetry config
│   └── slim/                   # SLIM gateway config
├── docker/
│   ├── Dockerfile.supervisor
│   └── Dockerfile.worker
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## 🚀 Quick Start

### Prerequisites

- Python 3.14+
- Docker & Docker Compose
- OpenAI API key (or other LLM provider)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd agentic-orchestrator
   ```

2. **Copy environment config:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Install dependencies:**
   ```bash
   pip install uv
   uv pip install -e .
   ```

4. **Run locally (without Docker):**
   ```bash
   uv run python -m orchestrator.agents.supervisor.main
   ```

### Docker Deployment

```bash
# Start all services
docker-compose up --build

# Services available at:
# - Supervisor: http://localhost:8000
# - Serviceability Agent: http://localhost:9001
# - Rate Agent: http://localhost:9002
# - Carrier Agent: http://localhost:9003
```

## 📡 API Usage

### Check Serviceability

```bash
curl -X POST http://localhost:8000/agent/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Can we ship from Mumbai to Hamburg?"}'
```

### Get Rate Quotes

```bash
curl -X POST http://localhost:8000/agent/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Get shipping quotes for 50kg from New York to London",
    "origin": "New York, USA",
    "destination": "London, UK"
  }'
```

### Book Shipment (with HITL for high-value orders)

```bash
curl -X POST http://localhost:8000/agent/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Book the cheapest option for my shipment",
    "order_id": "ORD-12345"
  }'
```

### Agent Discovery

```bash
# Get supervisor capabilities (OASF Agent Card)
curl http://localhost:8000/.well-known/agent.json
```

### HITL Approval (Admin)

```bash
# List pending approvals
curl http://localhost:8000/admin/pending-approvals

# Approve an order
curl -X POST http://localhost:8000/admin/approve \
  -H "Content-Type: application/json" \
  -d '{"interrupt_id": "hitl_abc123", "approver_id": "manager@company.com"}'
```

## 🔧 Configuration

Key environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPERVISOR_LLM` | LLM for supervisor | `openai/gpt-4-turbo` |
| `RATE_AGENT_LLM` | LLM for rate agent | `groq/llama-3.1-70b-versatile` |
| `MAX_AUTO_APPROVAL_LIMIT` | HITL threshold (USD) | `5000` |
| `DEFAULT_MESSAGE_TRANSPORT` | Transport type | `SLIM` |

## 📊 Observability

OpenTelemetry tracing is integrated:

```bash
# View traces (when using Jaeger)
open http://localhost:16686
```

## 🧪 Testing

```bash
# Run unit tests
uv run pytest tests/unit/ -v

# Run integration tests
uv run pytest tests/integration/ -v
```

## 📚 Reference Documentation

- [Reference Project Architecture](docs/reference_project_architecture.md)
- [Reference Project Class Diagram](docs/reference_project_class_diagram.md)

## 🏛️ Design Patterns

1. **Executor Pattern**: All agents implement `AgentExecutor` interface
2. **State Machine**: LangGraph manages workflow state
3. **Abstract Factory**: `AgntcyFactory` creates transports
4. **Dependency Inversion**: `LLMProvider` abstraction layer
5. **Strategy Pattern**: Pluggable LLM providers

## 🗺️ Roadmap

### V1 (Current)
- [x] Project infrastructure
- [x] LLM abstraction layer
- [x] Supervisor agent with LangGraph
- [x] Worker agents (Serviceability, Rate, Carrier)
- [x] Local Identity Service
- [x] HITL workflow

### V2 (Future)
- [ ] AGNTCY Identity Service integration
- [ ] Kubernetes deployment
- [ ] Advanced TBAC policies
- [ ] Real carrier API integrations
- [ ] Frontend UI

## 📄 License

MIT