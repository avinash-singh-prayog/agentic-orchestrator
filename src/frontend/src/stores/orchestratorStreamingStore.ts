/**
 * Orchestrator Streaming Store
 * 
 * Zustand store for managing streaming state from the orchestrator API.
 * Integrates with chat history store for multi-tenant context.
 */

import { create } from "zustand"
import type { OrchestratorStreamStep, StreamingState } from "@/types/streaming"
import type { FileAttachment } from "@/types/message"
import { API_ENDPOINTS } from "@/utils/const"
import { useChatHistoryStore } from "@/stores/chatHistoryStore"

interface OrchestratorStreamingActions {
  addEvent: (event: OrchestratorStreamStep) => void
  setFinalResponse: (response: string) => void
  setError: (error: string) => void
  setStreaming: (isStreaming: boolean) => void
  setComplete: (isComplete: boolean) => void
  startStreaming: (prompt: string, context?: Record<string, unknown>, attachments?: FileAttachment[]) => Promise<void>
  stopStreaming: () => void
  reset: () => void
}

type OrchestratorStreamingStore = StreamingState & OrchestratorStreamingActions & {
    abortController: AbortController | null
}

const initialState: StreamingState & { abortController: AbortController | null } = {
  status: "idle",
  events: [],
  finalResponse: null,
  error: null,
  currentOrderId: null,
  abortController: null,
}

const API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL || "http://localhost:8000"

export const useOrchestratorStreamingStore = create<OrchestratorStreamingStore>(
  (set, get) => ({
    ...initialState,

    addEvent: (event) => {
      set((state) => ({
        events: [...state.events, event],
        currentOrderId: event.order_id || state.currentOrderId,
      }))
    },

    setFinalResponse: (response) => {
      set({ finalResponse: response, status: "completed" })
    },

    setError: (error) => {
      set({ error, status: "error" })
    },

    setStreaming: (isStreaming) => {
      set({ status: isStreaming ? "streaming" : "idle" })
    },

    setComplete: () => {
      set({ status: "completed" })
    },

    reset: () => {
      set(initialState)
    },

    stopStreaming: () => {
      const { abortController } = get()
      if (abortController) {
        abortController.abort()
      }
      set({ status: "idle", abortController: null })
    },

    startStreaming: async (prompt, context, attachments) => {
      const { reset, addEvent, setFinalResponse, setError, stopStreaming } = get()
      
      // Stop any existing stream
      stopStreaming()

      // Create new abort controller
      const abortController = new AbortController()
      set({ abortController })

      // Get multi-tenant context from chat history store
      const chatStore = useChatHistoryStore.getState()
      const tenantId = chatStore.tenantId
      const userId = chatStore.userId
      const signal = abortController.signal

      if (!tenantId || !userId) {
        setError("User session not initialized. Please log in.")
        return
      }
      let threadId = chatStore.activeConversationId

      // Auto-create conversation if needed
      if (!threadId) {
        threadId = await chatStore.createNewConversation()
      }

      // Add user message to local history (with attachments)
      await chatStore.addUserMessage(prompt, attachments)

      reset()
      set({ status: "connecting", abortController }) // Re-set abortController as reset() might clear it

      try {
        // Prepare request body with attachments
        const requestBody: Record<string, unknown> = {
          prompt,
          tenant_id: tenantId,
          user_id: userId,
          thread_id: threadId,
          ...context,
        }

        // Use FormData if we have files, otherwise use JSON
        const hasFiles = attachments && attachments.length > 0 && attachments.some(att => att.file)
        
        let body: FormData | string
        let headers: HeadersInit
        
        if (hasFiles) {
          // Use FormData to send files directly (no base64 conversion needed!)
          const formData = new FormData()
          
          // Add text fields
          formData.append('prompt', prompt)
          formData.append('tenant_id', tenantId)
          formData.append('user_id', userId)
          formData.append('thread_id', threadId)
          
          // Add context fields
          Object.entries(context || {}).forEach(([key, value]) => {
            formData.append(key, String(value))
          })
          
          // Add files directly - no base64 conversion!
          const validAttachments = attachments.filter(att => att.file)
          validAttachments.forEach((att, index) => {
            formData.append(`file_${index}`, att.file!)
            formData.append(`file_${index}_id`, att.id)
            formData.append(`file_${index}_name`, att.name)
            formData.append(`file_${index}_type`, att.type)
            formData.append(`file_${index}_size`, String(att.size))
            formData.append(`file_${index}_file_type`, att.fileType)
          })
          
          body = formData
          // Don't set Content-Type - browser will set it with boundary
          headers = {}
        } else {
          // No files - use JSON as before
          if (attachments && attachments.length > 0) {
            requestBody.attachments = attachments.map(att => ({
              id: att.id,
              name: att.name,
              type: att.type,
              size: att.size,
              file_type: att.fileType,
            }))
          }
          body = JSON.stringify(requestBody)
          headers = {
            "Content-Type": "application/json",
          }
        }

        const response = await fetch(`${API_URL}${API_ENDPOINTS.PROMPT_STREAM}`, {
          method: "POST",
          headers,
          body,
          signal,
        })

        if (!response.ok) {
          // Try to get error details from response
          let errorMessage = `HTTP error! status: ${response.status}`
          let errorData: any = null
          try {
            errorData = await response.json()
            // Handle nested error detail structure
            if (errorData.detail) {
              if (typeof errorData.detail === 'string') {
                errorMessage = errorData.detail
              } else if (errorData.detail.message) {
                errorMessage = errorData.detail.message
              } else if (errorData.detail.error) {
                errorMessage = errorData.detail.message || errorData.detail.error
              }
            } else if (errorData.message) {
              errorMessage = errorData.message
            }
          } catch {
            // If response is not JSON, use status text
            errorMessage = response.statusText || errorMessage
          }
          const error = new Error(errorMessage)
          ;(error as any).detail = errorData
          throw error
        }

        // Check content-type to determine response format
        const contentType = response.headers.get("content-type") || ""
        
        // NDJSON streaming (application/x-ndjson or text/event-stream)
        const isStreaming = contentType.includes("ndjson") || 
                           contentType.includes("event-stream") ||
                           contentType.includes("octet-stream")
        
        // Handle sync JSON response (only if explicitly application/json)
        if (contentType.includes("application/json") && !isStreaming) {
          const data = await response.json()
          if (data.response) {
            // Add a single event showing the supervisor response
            addEvent({
              order_id: "",
              sender: "Supervisor",
              receiver: "",
              message: "Processing your request...",
              timestamp: new Date().toISOString(),
              state: "PROCESSING",
            })
            
            setFinalResponse(data.response)
            return
          }
        }

        // Handle streaming response (NDJSON)
        set({ status: "streaming" })

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error("No response body reader available")
        }

        const decoder = new TextDecoder()
        let buffer = ""
        let lastMessage = ""

        // Yield to the event loop after each event so the UI paints progressively (avoids all events appearing in one frame)
        const yieldToUI = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Parse NDJSON format (newline-delimited JSON)
          const lines = buffer.split("\n")
          buffer = lines.pop() || "" // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.trim()) {
              try {
                const data = JSON.parse(line)
                
                // New format: {"content": {"sender": "...", "message": "...", "node": "..."}}
                // Or: {"content": "plain text"} for old format
                if (data.content) {
                  let parsed = data.content
                  
                  // Try to parse if it's a JSON string
                  if (typeof parsed === "string") {
                    try {
                      parsed = JSON.parse(parsed)
                    } catch {
                      // It's just plain text
                      parsed = { sender: "System", message: parsed, node: "unknown" }
                    }
                  }
                  
                  if (parsed.sender && parsed.message) {
                    lastMessage = parsed.message
                    addEvent({
                      order_id: "",
                      sender: parsed.sender,
                      receiver: "",
                      message: parsed.message,
                      timestamp: new Date().toISOString(),
                      state: "PROCESSING",
                    })
                    await yieldToUI()
                  } else if (typeof data.content === "string") {
                    lastMessage = data.content
                    addEvent({
                      order_id: "",
                      sender: "System",
                      receiver: "",
                      message: data.content,
                      timestamp: new Date().toISOString(),
                      state: "PROCESSING",
                    })
                    await yieldToUI()
                  }
                }
              } catch (e) {
                console.error("Failed to parse streaming data:", e)
              }
            }
          }
        }

        // Set final response from last message
        if (lastMessage) {
          setFinalResponse(lastMessage)
        } else {
          set({ status: "completed" })
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error occurred"
        console.error("Streaming error:", error)
        setError(errorMessage)
        
        // If it's a 422 validation error, provide more helpful message
        if (error instanceof Error && error.message.includes("422")) {
          setError("File upload validation failed. Please ensure files are valid and try again.")
        }
      }
    },
  })
)

// Selector hooks for optimized re-renders
export const useStreamingEvents = () =>
  useOrchestratorStreamingStore((state) => state.events)

export const useStreamingStatus = () =>
  useOrchestratorStreamingStore((state) => state.status)

export const useStreamingFinalResponse = () =>
  useOrchestratorStreamingStore((state) => state.finalResponse)

export const useStreamingError = () =>
  useOrchestratorStreamingStore((state) => state.error)

// Action hooks - return stable references
export const useStartStreaming = () =>
  useOrchestratorStreamingStore((state) => state.startStreaming)

export const useResetStreaming = () =>
  useOrchestratorStreamingStore((state) => state.reset)

// Combined actions hook using getState for stable reference
export const useStreamingActions = () => {
  const store = useOrchestratorStreamingStore
  return {
    startStreaming: store.getState().startStreaming,
    stopStreaming: store.getState().stopStreaming,
    reset: store.getState().reset,
  }
}
