/**
 * Message Types for Chat Interface
 */

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  animate?: boolean
}

export interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
}
