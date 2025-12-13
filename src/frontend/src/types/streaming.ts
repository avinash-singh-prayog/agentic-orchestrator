/**
 * Streaming Types for Orchestrator Responses
 */

export interface OrchestratorStreamStep {
  order_id: string
  sender: string        // e.g., "supervisor", "serviceability", "rate", "carrier"
  receiver: string      
  message: string
  timestamp: string
  state: "PROCESSING" | "COMPLETED" | "PENDING_APPROVAL" | "ERROR"
}

export interface StreamingState {
  status: "idle" | "connecting" | "streaming" | "completed" | "error"
  events: OrchestratorStreamStep[]
  finalResponse: string | null
  error: string | null
  currentOrderId: string | null
}

export interface APIPromptRequest {
  prompt: string
  order_id?: string
  customer_id?: string
  origin?: string
  destination?: string
  shipments?: Record<string, unknown>[]
}

export interface APIPromptResponse {
  response: string
  order_id?: string
  status: string
}

export interface HITLInterrupt {
  interrupt_id: string
  order_id: string
  reason: string
  action: string
  context: {
    order_id?: string
    order_value?: number
    origin?: string
    destination?: string
  }
  status: "pending" | "approved" | "rejected"
  created_at: string
}

export interface HealthResponse {
  status: string
  version: string
  agent: string
}
