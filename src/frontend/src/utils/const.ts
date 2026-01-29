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
  SERVICEABILITY_AGENT: "serviceability-agent",
  BOOKING_AGENT: "booking-agent",
  TRANSACTION_RCA_AGENT: "transaction-rca-agent",
  ORCHESTRATOR_GROUP: "orchestrator-group",
} as const

// Edge identifiers
export const EDGE_IDS = {
  SUPERVISOR_TO_SLIM: "supervisor-to-slim",
  SLIM_TO_SERVICEABILITY: "slim-to-serviceability",
  SLIM_TO_RATE: "slim-to-rate",
  SLIM_TO_SERVICEABILITY_AGENT: "slim-to-serviceability-agent",
  SLIM_TO_BOOKING_AGENT: "slim-to-booking-agent",
  SLIM_TO_TRANSACTION_RCA_AGENT: "slim-to-transaction-rca-agent",
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
  PROMPT: "/supervisor-agent/v1/agent/run",           // Sync mode
  PROMPT_STREAM: "/supervisor-agent/v1/agent/stream", // Streaming mode (SSE)
  HEALTH: "/supervisor-agent/health",
  
  // Auth endpoints
  AUTH: {
    LOGIN: "/supervisor-agent/auth/login",
    REGISTER: "/supervisor-agent/auth/register",
    FORGOT_PASSWORD: "/supervisor-agent/auth/forgot-password",
    RESET_PASSWORD: "/supervisor-agent/auth/reset-password",
  },
  
  // Conversation history endpoints
  CONVERSATIONS: "/supervisor-agent/v1/conversations",
  CONVERSATION: (threadId: string) => `/supervisor-agent/v1/conversations/${threadId}`,
  
  // Admin endpoints (if implemented)
  AGENT_CARD: "/.well-known/agent.json",
  PENDING_APPROVALS: "/admin/pending-approvals",
  APPROVE: "/admin/approve",
  REJECT: "/admin/reject",
} as const

// Example prompts for the chat interface
export const EXAMPLE_PROMPTS = [
  "Analyze transaction failure for TXN-12345",
  "What caused the payment to fail for merchant ID 789?",
  "Perform root cause analysis on transaction error",
  "Why did transaction TXN-67890 get stuck in processing?",
  "Investigate the sync issue for transaction TXN-11111",
] as const

// Animation timing
export const ANIMATION_TIMING = {
  NODE_HIGHLIGHT_DURATION: 800,
  EDGE_FLOW_DURATION: 600,
  TRANSITION_DELAY: 200,
} as const
