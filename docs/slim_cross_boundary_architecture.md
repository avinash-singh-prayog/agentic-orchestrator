# SLIM Cross-Boundary Communication Architecture

## Analysis: Current vs. AGNTCY Full Vision

This document analyzes how agents coordinate via SLIM transporter in distributed systems, particularly for cross-organization agent discovery and communication.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Implementation Analysis](#current-implementation-analysis)
3. [AGNTCY Full Vision](#agntcy-full-vision)
4. [Architecture Gap Analysis](#architecture-gap-analysis)
5. [Ideal Cross-Boundary Architecture](#ideal-cross-boundary-architecture)
6. [Implementation Roadmap](#implementation-roadmap)
7. [References](#references)

---

## Executive Summary

The AGNTCY framework claims to enable an "Internet of Agents" where agents can discover and communicate with other agents running in completely different environments and organizations. This document examines:

1. **How our current implementation handles agent discovery and SLIM routing**
2. **What the full AGNTCY vision actually provides**
3. **The gap between our implementation and true cross-boundary communication**
4. **What architectural changes would be needed**

> [!IMPORTANT]
> Our current implementation is an **"Intranet of Agents"** (single-organization), not the full **"Internet of Agents"** (cross-organization) that AGNTCY envisions.

---

## Current Implementation Analysis

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT IMPLEMENTATION (Single-Org)                       │
│                                                                              │
│  ┌─────────────────────┐         REST API          ┌──────────────────────┐ │
│  │  Directory Service  │◄──────────────────────────►│    SLIM Transporter  │ │
│  │  (dir-apiserver)    │     (Agent Registry)       │  (Single Instance)   │ │
│  │  One Instance       │                            │  3.7.70.176:46357    │ │
│  └─────────────────────┘                            └──────────────────────┘ │
│           ▲                                                   ▲              │
│           │ dirctl push/search                                │ SLIM A2A    │
│           │                                                   │              │
│  ┌────────┴────────────────────────────────────────────────────┴──────────┐ │
│  │                         ALL AGENTS (Same Network)                       │ │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐             │ │
│  │  │  Supervisor  │  │  Serviceability  │  │    Booking    │             │ │
│  │  │    Agent     │  │     Agent        │  │     Agent     │             │ │
│  │  └──────────────┘  └──────────────────┘  └───────────────┘             │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Implementation Details

#### 1. Hardcoded SLIM Endpoint

All agents use the same SLIM endpoint from environment variable:

```python
# In supervisor_agent/agent/router.py (line 68)
self.slim_endpoint = os.getenv("SLIM_ENDPOINT", "http://orchestrator-slim:46357")

# In serviceability_agent/app/server_wrapper.py (line 140)
slim_endpoint = os.getenv("SLIM_ENDPOINT", "http://orchestrator-slim:46357")

# In booking_agent/app/server_wrapper.py (line 139)  
slim_endpoint = os.getenv("SLIM_ENDPOINT", "http://orchestrator-slim:46357")
```

#### 2. Single Directory Service

All agents register with one central directory:

```python
# In directory.py (line 26)
self.server_address = os.getenv("DIRECTORY_SERVICE_ADDR", "directory-service:8888")
```

#### 3. Topic-Only Discovery

Agent records only advertise SLIM topic in description, not the SLIM endpoint:

```json
{
  "name": "Serviceability Agent",
  "description": "Handles rate checking [TOPIC:logistics.serviceability.v1] [CAPABILITY:rate_fetching]",
  "version": "1.0.0"
}
```

#### 4. How Routing Works Currently

```python
# router.py - Discovery and Routing Flow
async def route_by_capability(self, capability: str, payload: str):
    # 1. Search Directory for capability tag
    search_term = f"[CAPABILITY:{capability}]"
    agent = self.directory.find_agent_by_name(search_term)
    
    # 2. Extract ONLY the topic from description
    topic = extract_topic_from_description(agent["description"])
    
    # 3. Route via HARDCODED SLIM endpoint
    transport = self.factory.create_transport(
        "SLIM",
        endpoint=self.slim_endpoint,  # ← Always the same!
        name=self.supervisor_identity
    )
```

### Limitations

| Aspect | Current Behavior | Limitation |
|--------|-----------------|------------|
| SLIM Endpoint | Single hardcoded value | Cannot connect to external SLIM |
| Directory | One instance | No cross-org discovery |
| Agent Records | Topic only | No routing endpoint info |
| Security | TLS disabled | No E2E encryption |

---

## AGNTCY Full Vision

### The "Internet of Agents" Architecture

AGNTCY envisions a truly distributed system with:

1. **Federated Agent Directory Service (ADS)** - DHT-based, cross-organizational
2. **SLIM Mesh Network** - Multiple peered SLIM nodes
3. **Agent Identity** - Cryptographically verifiable across boundaries
4. **Secure Communication** - MLS (Message Layer Security) for E2E encryption

### Federated Directory Service

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FEDERATED AGENT DIRECTORY SERVICE                         │
│                                                                              │
│      Organization A                     Organization B                       │
│  ┌──────────────────┐              ┌──────────────────┐                     │
│  │     ADS Node     │◄────DHT─────►│     ADS Node     │                     │
│  │  (dir-apiserver  │   Peering    │  (dir-apiserver  │                     │
│  │   + Kademlia)    │              │   + Kademlia)    │                     │
│  └──────────────────┘              └──────────────────┘                     │
│          │                                   │                               │
│          ▼                                   ▼                               │
│   Local Agents                        External Agents                        │
│                                                                              │
│  Federation Modes:                                                           │
│  • On-Demand Cross-Pull: Lazy artifact retrieval                            │
│  • Selective Replication: Policy-driven mirroring                           │
│  • Content-Addressed: SHA-256 digests for immutability                      │
│  • Cryptographic Signing: Sigstore for provenance                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Record with Full Locators

In the full AGNTCY vision, agent records contain complete routing information:

```json
{
  "cid": "bafkreiabcdef123...",
  "name": "Medical AI Agent",
  "description": "Provides medical analysis capabilities",
  "version": "2.0.0",
  "organization": "healthcare-ai-corp",
  "locators": [
    {
      "type": "SLIM",
      "endpoint": "slim.healthcare-ai.com:46357",
      "topic": "healthcare.medical-analysis.v2",
      "tls": {
        "enabled": true,
        "cert_chain": "..."
      }
    },
    {
      "type": "HTTP",
      "endpoint": "https://api.healthcare-ai.com/agent",
      "health_check": "/health"
    }
  ],
  "identity": {
    "public_key": "...",
    "signature": "..."
  },
  "capabilities": ["medical_analysis", "diagnosis_support", "drug_interaction"]
}
```

### SLIM Mesh Network

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SLIM MESH NETWORK                                    │
│                                                                              │
│  ┌────────────────────────┐         ┌────────────────────────┐              │
│  │  SLIM Node (Org A)     │◄──Mesh─►│  SLIM Node (Org B)     │              │
│  │  slim.org-a.com:46357  │ Peering │  slim.org-b.com:46357  │              │
│  └────────────────────────┘         └────────────────────────┘              │
│           ▲                                     ▲                            │
│           │                                     │                            │
│    ┌──────┴──────┐                       ┌──────┴──────┐                    │
│    │   Agent 1   │                       │   Agent 3   │                    │
│    │   Agent 2   │                       │   Agent 4   │                    │
│    └─────────────┘                       └─────────────┘                    │
│                                                                              │
│  SLIM Capabilities:                                                          │
│  • Unicast: Point-to-point communication                                    │
│  • Anycast: Any available instance of a service                             │
│  • Multicast: Broadcast to all topic subscribers                            │
│  • MLS: Message Layer Security for E2E encryption                           │
│  • Control Plane: Manages node federation and routing                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cross-Organization Discovery Flow

```
╔════════════════════════════════════════════════════════════════════════════╗
║             CROSS-ORGANIZATION AGENT DISCOVERY FLOW                         ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║  1. Agent A (Org A) needs capability "medical_analysis"                     ║
║                                                                             ║
║  2. Agent A → Org A's ADS                                                   ║
║     Query: "Search for [CAPABILITY:medical_analysis]"                       ║
║                                                                             ║
║  3. Org A's ADS doesn't have it locally                                     ║
║     → Queries federated peers via DHT                                       ║
║     → Finds Agent B registered in Org B's ADS                               ║
║                                                                             ║
║  4. Returns Agent Record with LOCATORS:                                     ║
║     {                                                                       ║
║       "name": "Medical AI Agent",                                           ║
║       "locators": [{                                                        ║
║         "type": "SLIM",                                                     ║
║         "endpoint": "slim.org-b.com:46357",  ← DIFFERENT SLIM!             ║
║         "topic": "org-b.medical.v1"                                         ║
║       }]                                                                    ║
║     }                                                                       ║
║                                                                             ║
║  5. Agent A creates transport to Org B's SLIM:                              ║
║     transport = factory.create_transport(                                   ║
║         "SLIM",                                                             ║
║         endpoint="slim.org-b.com:46357"  ← Dynamic from discovery!         ║
║     )                                                                       ║
║                                                                             ║
║  6. Agent A sends message to topic "org-b.medical.v1"                       ║
║     → Routed through Org B's SLIM to Medical Agent                          ║
║                                                                             ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

## Architecture Gap Analysis

### Comparison Table

| Feature | AGNTCY Full Vision | Our Current Implementation | Gap |
|---------|-------------------|---------------------------|-----|
| **Directory Service** | Federated DHT across orgs | Single instance | ❌ No federation |
| **SLIM Transporter** | Mesh with peering | Single node | ❌ No mesh |
| **Agent Records** | Full locators with endpoints | Topic in description only | ❌ No endpoint info |
| **Cross-Org Discovery** | DHT lookup across peers | Not possible | ❌ Not supported |
| **SLIM Endpoint** | Dynamic from discovery | Hardcoded env var | ❌ Static |
| **Security** | MLS E2E encryption | TLS disabled | ❌ No encryption |
| **Agent Identity** | Cryptographic signatures | None | ❌ No identity |
| **Content Addressing** | SHA-256 CIDs | Simple CIDs | ⚠️ Partial |

### Why This Gap Exists

1. **Early Stage Implementation**: Focus was on proving the concept within a single deployment
2. **dir-apiserver Limitations**: v0.6.0 has strict validation that rejects custom modules
3. **SLIM Control Plane**: Not deployed - only data plane running
4. **Security Complexity**: MLS and cryptographic identity require additional infrastructure

---

## Ideal Cross-Boundary Architecture

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          INTERNET OF AGENTS (IoA)                                    │
│                                                                                      │
│  ╔═══════════════════════════════════════════════════════════════════════════════╗  │
│  ║                          CONTROL PLANE                                         ║  │
│  ║  ┌─────────────────┐                         ┌─────────────────┐              ║  │
│  ║  │  ADS (Org A)    │◄───DHT Federation──────►│  ADS (Org B)    │              ║  │
│  ║  │  + Kademlia     │                         │  + Kademlia     │              ║  │
│  ║  └─────────────────┘                         └─────────────────┘              ║  │
│  ║                                                                                ║  │
│  ║  ┌─────────────────┐                         ┌─────────────────┐              ║  │
│  ║  │ SLIM Control    │◄───Mesh Coordination───►│ SLIM Control    │              ║  │
│  ║  │ Plane (Org A)   │                         │ Plane (Org B)   │              ║  │
│  ║  └─────────────────┘                         └─────────────────┘              ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════════╝  │
│                                                                                      │
│  ╔═══════════════════════════════════════════════════════════════════════════════╗  │
│  ║                           DATA PLANE                                           ║  │
│  ║                                                                                ║  │
│  ║  ┌───────────────────────────────┐   ┌───────────────────────────────┐        ║  │
│  ║  │     ORGANIZATION A            │   │     ORGANIZATION B             │        ║  │
│  ║  │                               │   │                                │        ║  │
│  ║  │  ┌──────────────────────┐    │   │    ┌──────────────────────┐   │        ║  │
│  ║  │  │  SLIM Data Plane     │◄───┼───┼───►│  SLIM Data Plane     │   │        ║  │
│  ║  │  │  slim.org-a.com:46357│    │   │    │  slim.org-b.com:46357│   │        ║  │
│  ║  │  └──────────────────────┘    │   │    └──────────────────────┘   │        ║  │
│  ║  │           ▲                  │   │             ▲                 │        ║  │
│  ║  │           │ SLIM A2A         │   │             │ SLIM A2A        │        ║  │
│  ║  │    ┌──────┴──────┐           │   │      ┌──────┴──────┐          │        ║  │
│  ║  │    │ Supervisor  │           │   │      │ Medical AI  │          │        ║  │
│  ║  │    │ Serviceability│         │   │      │ Diagnostic  │          │        ║  │
│  ║  │    │ Booking     │           │   │      │ Research    │          │        ║  │
│  ║  │    └─────────────┘           │   │      └─────────────┘          │        ║  │
│  ║  └───────────────────────────────┘   └───────────────────────────────┘        ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════════╝  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Required Changes

#### 1. Enhanced Agent Records

```json
{
  "cid": "bafkreiabcdef123...",
  "name": "Serviceability Agent",
  "description": "Handles shipping rate calculations and route validation",
  "version": "1.0.0",
  "organization": "logistics-platform",
  "locators": [
    {
      "type": "SLIM",
      "endpoint": "${SLIM_PUBLIC_ENDPOINT}",
      "topic": "logistics.serviceability.v1",
      "tls": { "enabled": true }
    }
  ],
  "capabilities": ["rate_fetching", "route_validation"],
  "identity": {
    "type": "sigstore",
    "public_key": "..."
  }
}
```

#### 2. Dynamic Router Implementation

```python
class DiscoveryRouter:
    async def route_by_capability(self, capability: str, payload: str) -> str:
        # 1. Search federated directory
        agent = self.directory.find_agent_by_capability(capability)
        
        # 2. Extract BOTH endpoint AND topic from locators
        locator = self._get_slim_locator(agent)
        endpoint = locator["endpoint"]  # ← Dynamic!
        topic = locator["topic"]
        
        # 3. Create transport to DISCOVERED endpoint
        transport = self.factory.create_transport(
            "SLIM",
            endpoint=endpoint,  # ← Not hardcoded!
            tls_config=locator.get("tls")
        )
        
        # 4. Route message
        return await self._send_via_slim(transport, topic, payload)
```

#### 3. Directory Federation

```yaml
# ADS Configuration with DHT Peering
federation:
  enabled: true
  mode: "on-demand-cross-pull"
  peers:
    - "ads.partner-org.com:8888"
    - "ads.healthcare-ai.com:8888"
  dht:
    bootstrap_nodes:
      - "dht-bootstrap.agntcy.org:4001"
```

#### 4. SLIM Mesh Configuration

```yaml
# SLIM with Mesh Peering
services:
  slim/0:
    node_id: "slim-org-a-01"
    dataplane:
      servers:
        - endpoint: "0.0.0.0:46357"
          tls:
            enabled: true
            cert: "/certs/slim.crt"
            key: "/certs/slim.key"
    controlplane:
      enabled: true
      peers:
        - "slim.partner-org.com:46358"
      mesh:
        routing: "anycast"
```

---

## Implementation Roadmap

### Phase 1: Foundation (Current + Improvements)

- [x] Single-org SLIM communication
- [x] Directory-based agent discovery
- [x] Capability-based routing
- [ ] Add `locators` to agent records
- [ ] Dynamic SLIM endpoint from discovery
- [ ] Enable TLS on SLIM

### Phase 2: Security & Identity

- [ ] Enable MLS on SLIM data plane
- [ ] Implement agent identity with Sigstore
- [ ] Add cryptographic signatures to agent records
- [ ] Mutual TLS between SLIM nodes

### Phase 3: Federation

- [ ] Deploy SLIM control plane
- [ ] Configure DHT peering on ADS
- [ ] Implement cross-org discovery
- [ ] SLIM mesh peering

### Phase 4: Production IoA

- [ ] Multi-region SLIM mesh
- [ ] Federated identity across orgs
- [ ] Policy-based routing
- [ ] Full OASF compliance

---

## References

- [AGNTCY Official Site](https://agntcy.org)
- [SLIM Repository](https://github.com/agntcy/slim)
- [Agent Directory Service](https://github.com/agntcy/dir)
- [Open Agent Schema Framework (OASF)](https://github.com/agntcy/oasf)
- [IETF MLS RFC 9420](https://datatracker.ietf.org/doc/rfc9420/)
- [Linux Foundation Announcement](https://www.linuxfoundation.org/press/agntcy-open-source-framework)

---

## Appendix: Key Takeaways

### How Agents Know the SLIM Address (Current vs. Ideal)

| Aspect | Current Implementation | Ideal IoA Implementation |
|--------|----------------------|--------------------------|
| **How agent knows SLIM address** | Hardcoded `SLIM_ENDPOINT` env var | Dynamic from agent record `locators` |
| **Where SLIM address is stored** | Environment variable | Agent record in federated ADS |
| **Cross-org capability** | Not possible | Via DHT + locators |
| **Discovery returns** | Topic only | Endpoint + Topic + TLS config |

### The Core Insight

> **The "Internet of Agents" requires that agent discovery returns not just WHAT topic to use, but WHERE the SLIM transporter is located.**

Our current implementation assumes a shared SLIM, making cross-boundary communication impossible. True IoA requires federated discovery returning complete routing information.
