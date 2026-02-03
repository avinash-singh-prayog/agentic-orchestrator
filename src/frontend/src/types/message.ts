/**
 * Message Types for Chat Interface
 */

export interface AgentActivityEvent {
  sender: string
  receiver?: string
  message: string
  state?: string
}

export interface FileAttachment {
  id: string
  name: string
  type: string
  size: number
  fileType: 'image' | 'text'  // Classification for routing
  url?: string       // Temporary URL for preview
  file?: File        // The actual File object - sent directly via FormData (no base64 needed)
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  animate?: boolean
  activity?: AgentActivityEvent[]
  attachments?: FileAttachment[]
}

export interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
}
