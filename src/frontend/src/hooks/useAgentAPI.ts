/**
 * useAgentAPI Hook
 * 
 * Central hook for API communication with the orchestrator.
 */

import { useState, useRef, useCallback } from "react"
import axios, { type AxiosError } from "axios"
import type { 
  APIPromptRequest, 
  APIPromptResponse, 
  HITLInterrupt, 
  HealthResponse 
} from "@/types/streaming"
import { API_ENDPOINTS } from "@/utils/const"

const API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL || "http://localhost:8000"

interface UseAgentAPIReturn {
  loading: boolean
  error: string | null
  sendMessage: (prompt: string, context?: Partial<APIPromptRequest>) => Promise<string>
  getHealth: () => Promise<HealthResponse>
  getPendingApprovals: () => Promise<HITLInterrupt[]>
  approveInterrupt: (interruptId: string, approverId?: string) => Promise<void>
  rejectInterrupt: (interruptId: string, reason?: string) => Promise<void>
  cancel: () => void
}

export const useAgentAPI = (): UseAgentAPIReturn => {
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (prompt: string, context?: Partial<APIPromptRequest>): Promise<string> => {
      setLoading(true)
      setError(null)
      
      const controller = new AbortController()
      abortRef.current = controller

      try {
        const response = await axios.post<APIPromptResponse>(
          `${API_URL}${API_ENDPOINTS.PROMPT}`,
          { prompt, ...context },
          { signal: controller.signal }
        )
        return response.data.response
      } catch (err) {
        const axiosError = err as AxiosError<{ detail?: string }>
        const errorMessage = 
          axiosError.response?.data?.detail || 
          axiosError.message || 
          "Failed to send message"
        setError(errorMessage)
        throw new Error(errorMessage)
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const getHealth = useCallback(async (): Promise<HealthResponse> => {
    try {
      const response = await axios.get<HealthResponse>(`${API_URL}${API_ENDPOINTS.HEALTH}`)
      return response.data
    } catch (err) {
      const axiosError = err as AxiosError
      throw new Error(axiosError.message || "Failed to get health status")
    }
  }, [])

  const getPendingApprovals = useCallback(async (): Promise<HITLInterrupt[]> => {
    try {
      const response = await axios.get<{ pending: HITLInterrupt[] }>(
        `${API_URL}${API_ENDPOINTS.PENDING_APPROVALS}`
      )
      return response.data.pending
    } catch (err) {
      const axiosError = err as AxiosError
      throw new Error(axiosError.message || "Failed to get pending approvals")
    }
  }, [])

  const approveInterrupt = useCallback(
    async (interruptId: string, approverId: string = "admin"): Promise<void> => {
      try {
        await axios.post(`${API_URL}${API_ENDPOINTS.APPROVE}`, {
          interrupt_id: interruptId,
          approver_id: approverId,
        })
      } catch (err) {
        const axiosError = err as AxiosError
        throw new Error(axiosError.message || "Failed to approve interrupt")
      }
    },
    []
  )

  const rejectInterrupt = useCallback(
    async (interruptId: string, reason: string = ""): Promise<void> => {
      try {
        await axios.post(`${API_URL}${API_ENDPOINTS.REJECT}`, {
          interrupt_id: interruptId,
          reason,
        })
      } catch (err) {
        const axiosError = err as AxiosError
        throw new Error(axiosError.message || "Failed to reject interrupt")
      }
    },
    []
  )

  const cancel = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return {
    loading,
    error,
    sendMessage,
    getHealth,
    getPendingApprovals,
    approveInterrupt,
    rejectInterrupt,
    cancel,
  }
}
