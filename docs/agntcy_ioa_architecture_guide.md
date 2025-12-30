# AGNTCY IoA Architecture Guide

## Multi-Agent Communication & Discovery

This document defines the architectural patterns, communication protocols, and best practices for building agents in the Agentic Orchestrator system following the **AGNTCY Internet of Agents (IoA)** architecture.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Communication Protocols](#communication-protocols)
3. [Core Components](#core-components)
4. [Agent Development Guide](#agent-development-guide)
5. [Directory Service Integration](#directory-service-integration)
6. [SLIM Transport Integration](#slim-transport-integration)
7. [Best Practices](#best-practices)
8. [Anti-Patterns (What NOT to Do)](#anti-patterns)
9. [Checklist for New Agents](#checklist-for-new-agents)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTROL PLANE                                      │
│  ┌─────────────────────┐                                                    │
│  │  Directory Service  │  ← REST API (Agent Registry)                       │
│  │  (dir-apiserver)    │                                                    │
│  └─────────────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
        ▲                                                     
        │ REST API (dirctl CLI)                               
        │ • Register agents                                   
        │ • Search by capability                              
        │ • Discover agent metadata                           
        ▼                                                     
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA PLANE                                         │
│                                                                              │
│  ┌──────────────┐    SLIM A2A    ┌───────────────────┐                      │
│  │  Supervisor  │◄──────────────►│  SLIM Transporter │                      │
│  │    Agent     │                │   (Message Bus)   │                      │
│  └──────────────┘                └───────────────────┘                      │
│                                          ▲                                   │
│                                          │ SLIM A2A                          │
│                          ┌───────────────┼───────────────┐                  │
│                          ▼               ▼               ▼                  │
│                   ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│                   │Serviceability│ │  Booking   │  │  Future    │           │
│                   │   Agent    │  │   Agent    │  │  Agents    │           │
│                   └────────────┘  └────────────┘  └────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Decoupled Discovery** | Agents don't know each other directly; they discover via Directory Service |
| **Capability-Based Routing** | Route by capability (e.g., "rate_fetching"), not agent name |
| **Dual-Plane Architecture** | Control Plane (REST) for discovery, Data Plane (SLIM) for messaging |
| **Stateless Agents** | Each agent request must be self-contained |

---

## Communication Protocols

### Protocol Comparison

| Protocol | Used For | When |
|----------|----------|------|
| **REST API** | Agent Registration, Discovery | Supervisor → Directory Service |
| **SLIM A2A** | Agent-to-Agent Messaging | Supervisor → Worker Agents |
| **HTTP** | External API calls, Health checks | Agents → External Services |

### Message Flow

```
1. User Request → [HTTP] → Supervisor Agent
2. Supervisor → [REST/CLI] → Directory Service (find capable agent)
3. Directory → [REST/CLI] → Supervisor (returns agent record with SLIM topic)
4. Supervisor → [SLIM A2A] → SLIM Transporter → Worker Agent
5. Worker Agent → [SLIM A2A] → SLIM Transporter → Supervisor
6. Supervisor → [HTTP] → User Response
```

---

## Core Components

### 1. Directory Service (`dir-apiserver`)

**Purpose**: Central registry for agent metadata and capabilities.

**Interaction Method**: CLI tool (`dirctl`) which calls REST APIs internally.

```bash
# Register an agent
dirctl push agent_record.json

# Search for agents by capability
dirctl search -k "[CAPABILITY:rate_fetching]"

# Get agent details
dirctl get <agent-cid>
```

### 2. SLIM Transporter

**Purpose**: Message bus for Agent-to-Agent (A2A) communication.

**Key Concepts**:
- **Topics**: Each agent listens on a unique topic (e.g., `logistics.serviceability.v1`)
- **A2A Protocol**: Standardized message format for inter-agent communication

### 3. Agent Records (OASF Schema)

Every agent must have an `agent_record.json` following OASF schema:

```json
{
  "cid": "unique-content-id",
  "name": "Serviceability Agent",
  "description": "Handles rate checking [TOPIC:logistics.serviceability.v1] [CAPABILITY:rate_fetching] [CAPABILITY:route_validation]",
  "version": "1.0.0",
  "skills": [
    {
      "name": "check_rates",
      "description": "Check shipping rates between locations"
    }
  ]
}
```

> ⚠️ **Current Workaround**: Due to `dir-apiserver` v0.6.0 validation limitations, we embed TOPIC and CAPABILITY tags in the `description` field.

---

## Agent Development Guide

### Step 1: Define Agent Record

Create `agent_record.json` with:
- Unique `name` and `cid`
- Capabilities as `[CAPABILITY:xxx]` tags in description
- SLIM topic as `[TOPIC:xxx]` tag in description
- Human-readable `skills` array

```json
{
  "name": "My New Agent",
  "description": "Does amazing things [TOPIC:my.agent.v1] [CAPABILITY:amazing_task]",
  "version": "1.0.0",
  "skills": [
    {"name": "do_amazing_things", "description": "Performs amazing tasks"}
  ]
}
```

### Step 2: Implement SLIM Listener

Your agent must listen on its advertised SLIM topic:

```python
from agntcy_app_sdk import AgntcyFactory

# The topic MUST match what's in agent_record.json
PERSONAL_TOPIC = "my.agent.v1"

factory = AgntcyFactory("my_agent")
transport = factory.create_transport("SLIM", endpoint=SLIM_ENDPOINT, name="my-agent")
server = await factory.create_a2a_server(
    transport=transport,
    personal_topic=PERSONAL_TOPIC,  # This is what you advertise
    request_handler=handle_request
)
await server.run()
```

### Step 3: Register with Directory

At startup, register your agent:

```python
from agent.directory import DirectoryClient

client = DirectoryClient()
client.register_agent()  # Pushes agent_record.json to Directory
```

### Step 4: Implement Request Handler

```python
async def handle_request(request) -> str:
    """Handle incoming A2A requests."""
    user_message = extract_message(request)
    
    # Process the request
    result = await process_task(user_message)
    
    return result
```

---

## Directory Service Integration

### Registration Pattern

```python
# In agent startup (e.g., FastAPI lifespan)
@asynccontextmanager
async def lifespan(app):
    # Register with Directory at startup
    try:
        client = DirectoryClient()
        client.register_agent()
        logger.info("Registered with Directory Service")
    except Exception as e:
        logger.warning(f"Directory registration failed: {e}")
    
    yield
```

### Discovery Pattern (Supervisor)

```python
async def route_by_capability(capability: str, message: str):
    # 1. Search Directory for capability
    search_term = f"[CAPABILITY:{capability}]"
    agent = directory.find_agent_by_name(search_term)
    
    # 2. Extract SLIM topic from agent description
    topic = extract_topic_from_description(agent["description"])
    
    # 3. Route via SLIM
    response = await send_via_slim(topic, message)
    return response
```

---

## SLIM Transport Integration

### Creating a SLIM Client (Sender)

```python
from agntcy_app_sdk import AgntcyFactory

factory = AgntcyFactory("sender-agent")
transport = factory.create_transport("SLIM", endpoint=SLIM_ENDPOINT)
client = await factory.create_client("A2A", agent_topic=TARGET_TOPIC, transport=transport)

# Send message
response = await client.send_message(request)
```

### Creating a SLIM Server (Receiver)

```python
server = await factory.create_a2a_server(
    transport=transport,
    personal_topic="my.agent.topic.v1",
    request_handler=my_handler
)
await server.run()
```

---

## Best Practices

### ✅ DO

| Practice | Why |
|----------|-----|
| **Use capability-based routing** | Supervisor only knows capabilities, not agent names |
| **Embed metadata in description** | Workaround for dir-apiserver v0.6.0 limitations |
| **Run agents in "dual" mode** | Support both HTTP (health checks) and SLIM (A2A) |
| **Make requests self-contained** | Agents are stateless; include all context |
| **Register at startup** | Ensure agent is discoverable before accepting requests |
| **Use semantic versioning for topics** | e.g., `logistics.serviceability.v1` → `v2` for breaking changes |
| **Emit events for observability** | Use `dispatch_custom_event` for timeline visibility |

### ❌ DON'T (Anti-Patterns)

| Anti-Pattern | Why It's Bad |
|--------------|--------------|
| **Hardcoding agent names in Supervisor** | Defeats dynamic discovery |
| **Direct HTTP calls between agents** | Bypasses A2A protocol |
| **Storing state between requests** | Agents must be stateless |
| **Guessing SLIM topics** | Always discover via Directory |
| **Skipping Directory registration** | Agent won't be discoverable |
| **Using REST for A2A messaging** | Use SLIM for agent communication |

---

## Anti-Patterns

### ❌ Hardcoded Agent References

```python
# BAD - Supervisor knows agent name
@tool
async def call_serviceability_agent(prompt: str):
    return await call_agent("serviceability-agent", prompt)

# GOOD - Supervisor only knows capabilities  
@tool
async def delegate_to_capability(capability: str, message: str):
    return await route_by_capability(capability, message)
```

### ❌ Direct Agent Communication

```python
# BAD - Direct HTTP call bypasses discovery
response = requests.post("http://serviceability-agent:8001/api", ...)

# GOOD - Discover via Directory, route via SLIM
agent = directory.find_by_capability("rate_fetching")
topic = extract_topic(agent)
response = await slim_client.send(topic, message)
```

### ❌ Stateful Agent Assumptions

```python
# BAD - Assumes agent remembers context
await delegate("rate_fetching", "now with 5kg")  # What route?

# GOOD - Self-contained request
await delegate("rate_fetching", "Check rates from 713333 to 10003 for 5kg")
```

---

## Checklist for New Agents

### Before Development

- [ ] Define unique agent name and CID
- [ ] Identify capabilities this agent provides
- [ ] Choose a SLIM topic (format: `domain.service.vX`)
- [ ] Ensure SLIM transporter is accessible

### During Development

- [ ] Create `agent_record.json` with proper tags
- [ ] Implement SLIM server listener
- [ ] Add Directory registration at startup
- [ ] Implement request handler
- [ ] Add health check endpoint (`/health`)
- [ ] Emit events for observability

### Deployment

- [ ] Configure `SLIM_ENDPOINT` environment variable
- [ ] Run in "dual" mode (HTTP + SLIM)
- [ ] Verify Directory registration succeeds
- [ ] Test discovery from Supervisor
- [ ] Verify SLIM communication works

### Post-Deployment

- [ ] Monitor agent logs
- [ ] Verify agent appears in Directory searches
- [ ] Test end-to-end flow from user request

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SLIM_ENDPOINT` | SLIM transporter URL | `http://orchestrator-slim:46357` |
| `DIRECTORY_ENDPOINT` | Directory service URL | `http://dir-apiserver:8080` |
| `AGENT_MODE` | Run mode | `dual` (HTTP + SLIM) |

---

## Future Improvements

1. **Full OASF Compliance**: Once dir-apiserver supports custom fields, migrate from description tags to proper `locators` and `extension_data`
2. **Record Signing**: Add cryptographic signatures to agent records
3. **CI/CD Registration**: Automate agent registration in deployment pipelines
4. **MCP Server Support**: Extend patterns for Model Context Protocol servers

---

## References

- [AGNTCY IoA Specification](https://github.com/agntcy)
- [OASF Schema](https://github.com/agntcy/oasf)
- [SLIM Transporter Documentation](https://github.com/agntcy/slim)
