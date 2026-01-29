# Quick Start Guide - Running the Orchestrator System

## Prerequisites

1. **Docker & Docker Compose** installed
2. **Environment variables** set (API keys for LLM providers)

## Step 1: Set Up Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# LLM Provider API Keys
OPENROUTER_API_KEY=your_openrouter_key_here
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here  # For Transaction RCA Agent

# LLM Model Configuration
SUPERVISOR_LLM=openrouter/openai/gpt-4o-mini
SERVICEABILITY_AGENT_LLM=openrouter/openai/gpt-4o-mini
BOOKING_AGENT_LLM=openrouter/openai/gpt-4o-mini
TRANSACTION_RCA_AGENT_LLM=gemini/gemini-3-flash-preview

# SLIM Transport (using remote EC2 instance)
SLIM_ENDPOINT=http://3.7.70.176:46357

# Port Configuration (optional - defaults shown)
FRONTEND_PORT=3000
SUPERVISOR_AGENT_PORT=9004
SERVICEABILITY_AGENT_PORT=9003
BOOKING_AGENT_PORT=9005
TRANSACTION_RCA_AGENT_PORT=9006

# Database (for supervisor agent conversation history)
DATABASE_URL=postgresql://orchestrator_supervisor_agent:pFaiA88gRFFwrF@prayog-orchestrator-sandbox.c7geye6morpj.ap-south-1.rds.amazonaws.com:5432/orchestrator_supervisor_prod
```

## Step 2: Start All Services

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode (background)
docker-compose up --build -d
```

## Step 3: Access the Frontend

Once all services are running, open your browser and navigate to:

**Frontend UI:** http://localhost:3000

(Or the port specified in `FRONTEND_PORT` environment variable)

## Step 4: Test the System

### Option 1: Via Frontend UI
1. Open http://localhost:3000
2. Register/Login (first time users need to register)
3. Start chatting with the orchestrator:
   - "Check shipping rates from Mumbai to London for 5kg"
   - "Book a shipment from 400001 to 110001"
   - "Analyze transaction TXN12345 for root cause" (for Transaction RCA)

### Option 2: Via API (Direct)

**Check Serviceability:**
```bash
curl -X POST http://localhost:9004/supervisor-agent/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Check shipping rates from Mumbai 400001 to Delhi 110001 for 2kg",
    "tenant_id": "test-tenant",
    "user_id": "test-user"
  }'
```

**Transaction RCA Analysis:**
```bash
curl -X POST http://localhost:9004/supervisor-agent/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze transaction TXN123 for root cause. Transaction context: {\"transaction_id\": \"TXN123\", \"checkpoints\": [{\"checkpoint_name\": \"ingestion\", \"status\": \"success\"}, {\"checkpoint_name\": \"authorization\", \"status\": \"success\"}, {\"checkpoint_name\": \"routing\", \"status\": \"pending\"}]}",
    "tenant_id": "test-tenant",
    "user_id": "test-user"
  }'
```

## Service URLs

Once running, services are available at:

| Service | URL | Port |
|---------|-----|------|
| **Frontend UI** | http://localhost:3000 | 3000 |
| **Supervisor Agent** | http://localhost:9004 | 9004 |
| **Serviceability Agent** | http://localhost:9003 | 9003 |
| **Booking Agent** | http://localhost:9005 | 9005 |
| **Transaction RCA Agent** | http://localhost:9006 | 9006 |

## Health Checks

Check if services are running:

```bash
# Supervisor Agent
curl http://localhost:9004/supervisor-agent/health

# Serviceability Agent
curl http://localhost:9003/serviceability-agent/health

# Booking Agent
curl http://localhost:9005/booking-agent/health

# Transaction RCA Agent
curl http://localhost:9006/transaction-rca-agent/health
```

## Troubleshooting

### Services won't start
1. Check Docker is running: `docker ps`
2. Check logs: `docker-compose logs [service-name]`
3. Verify environment variables are set correctly

### Frontend can't connect to backend
1. Check `VITE_ORCHESTRATOR_API_URL` in docker-compose.yml points to supervisor-agent:9004
2. Verify supervisor agent is running: `curl http://localhost:9004/supervisor-agent/health`

### SLIM connection issues
1. Verify SLIM_ENDPOINT is accessible
2. Check network connectivity to the SLIM server

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f supervisor-agent
docker-compose logs -f transaction-rca-agent
```

## Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```
