/**
 * Constants and Identifiers
 * 
 * Central location for all node IDs, edge IDs, and configuration constants.
 */

// Node identifiers for the orchestrator graph
export const NODE_IDS = {
  SUPERVISOR: "supervisor",
  SLIM_TRANSPORT: "slim-transport",
  SERVICEABILITY: "serviceability",
  RATE_AGENT: "rate-agent",
  CARRIER: "carrier",
  ORCHESTRATOR_GROUP: "orchestrator-group",
} as const

// Edge identifiers
export const EDGE_IDS = {
  SUPERVISOR_TO_SLIM: "supervisor-to-slim",
  SLIM_TO_SERVICEABILITY: "slim-to-serviceability",
  SLIM_TO_RATE: "slim-to-rate",
  SLIM_TO_CARRIER: "slim-to-carrier",
} as const

// Node types for ReactFlow
export const NODE_TYPES = {
  CUSTOM: "customNode",
  TRANSPORT: "transportNode",
} as const

// Edge types for ReactFlow
export const EDGE_TYPES = {
  CUSTOM: "custom",
  ANIMATED: "animated",
} as const

// Handle positions
export const HANDLE_TYPES = {
  SOURCE: "source",
  TARGET: "target",
  ALL: "all",
} as const

// Agent status colors
export const AGENT_STATUS = {
  IDLE: "idle",
  PROCESSING: "processing",
  COMPLETED: "completed",
  ERROR: "error",
} as const

// API endpoints - match Supervisor Agent API
export const API_ENDPOINTS = {
  // Supervisor Agent endpoints
  PROMPT: "/supervisor/v1/agent/run",           // Sync mode
  PROMPT_STREAM: "/supervisor/v1/agent/stream", // Streaming mode (SSE)
  HEALTH: "/health",
  
  // Conversation history endpoints
  CONVERSATIONS: "/supervisor/v1/conversations",
  CONVERSATION: (threadId: string) => `/supervisor/v1/conversations/${threadId}`,
  
  // Admin endpoints (if implemented)
  AGENT_CARD: "/.well-known/agent.json",
  PENDING_APPROVALS: "/admin/pending-approvals",
  APPROVE: "/admin/approve",
  REJECT: "/admin/reject",
} as const

// Example prompts for the chat interface
export const EXAMPLE_PROMPTS = [
  "Can we ship from Mumbai to London?",
  "Get shipping quotes for 50kg from New York to Tokyo",
  "What carriers are available for international shipping?",
  "Book the cheapest option for my shipment",
  "Check serviceability from Los Angeles to Berlin",
] as const

// Animation timing
export const ANIMATION_TIMING = {
  NODE_HIGHLIGHT_DURATION: 800,
  EDGE_FLOW_DURATION: 600,
  TRANSITION_DELAY: 200,
} as const
