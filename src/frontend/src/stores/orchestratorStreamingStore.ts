/**
 * Orchestrator Streaming Store
 * 
 * Zustand store for managing streaming state from the orchestrator API.
 */

import { create } from "zustand"
import type { OrchestratorStreamStep, StreamingState } from "@/types/streaming"
import { API_ENDPOINTS } from "@/utils/const"

interface OrchestratorStreamingActions {
  addEvent: (event: OrchestratorStreamStep) => void
  setFinalResponse: (response: string) => void
  setError: (error: string) => void
  setStreaming: (isStreaming: boolean) => void
  setComplete: (isComplete: boolean) => void
  startStreaming: (prompt: string, context?: Record<string, unknown>) => Promise<void>
  reset: () => void
}

type OrchestratorStreamingStore = StreamingState & OrchestratorStreamingActions

const initialState: StreamingState = {
  status: "idle",
  events: [],
  finalResponse: null,
  error: null,
  currentOrderId: null,
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

    startStreaming: async (prompt, context) => {
      const { reset, addEvent, setFinalResponse, setError } = get()

      reset()
      set({ status: "connecting" })

      try {
        const response = await fetch(`${API_URL}${API_ENDPOINTS.PROMPT_STREAM}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            prompt,
            ...context,
          }),
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        set({ status: "streaming" })

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error("No response body reader available")
        }

        const decoder = new TextDecoder()
        let buffer = ""

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
                
                if (data.response) {
                  // Try to parse inner response as JSON (for streaming events)
                  try {
                    const innerData = JSON.parse(data.response.replace(/'/g, '"'))
                    if (innerData.sender && innerData.message) {
                      addEvent({
                        order_id: innerData.order_id || "",
                        sender: innerData.sender,
                        receiver: innerData.receiver || "",
                        message: innerData.message,
                        timestamp: innerData.timestamp || new Date().toISOString(),
                        state: innerData.state || "PROCESSING",
                      })
                    }
                  } catch {
                    // If not parseable, treat as final response
                    setFinalResponse(data.response)
                  }
                }
              } catch (e) {
                console.error("Failed to parse streaming data:", e)
              }
            }
          }
        }

        set({ status: "completed" })
      } catch (error) {
        setError(error instanceof Error ? error.message : "Unknown error occurred")
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

export const useStreamingActions = () =>
  useOrchestratorStreamingStore((state) => ({
    startStreaming: state.startStreaming,
    reset: state.reset,
  }))
