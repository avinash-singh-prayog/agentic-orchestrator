/**
 * Message Types for Chat Interface
 */

export interface AgentActivityEvent {
  sender: string
  receiver?: string
  message: string
  state?: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  animate?: boolean
  activity?: AgentActivityEvent[]
}

export interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
}
