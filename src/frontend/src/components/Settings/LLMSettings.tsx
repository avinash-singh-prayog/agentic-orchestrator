/**
 * LLM Settings Component
 * 
 * Modal dialog for configuring LLM provider, model, and API key.
 */

import React, { useState, useEffect } from "react"
import { createPortal } from "react-dom"
import { X, Eye, EyeOff, AlertCircle, Loader } from "lucide-react"
import { API_ENDPOINTS } from "@/utils/const"
import { useTheme } from "@/contexts/ThemeContext"

const API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL || 'http://localhost:8000'

interface LLMSettingsProps {
  isOpen: boolean
  onClose: () => void
  userId: string
  onApiKeySaved?: () => void
}

interface LLMConfig {
  provider: string
  model: string
  has_api_key: boolean
  updated_at: string | null
}

const AVAILABLE_PROVIDERS = {
  openai: {
    models: ["gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4-turbo", "gpt-4o"],
    api_key_prefix: "sk-"
  },
  anthropic: {
    models: ["claude-opus-4.5", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    api_key_prefix: "sk-ant-"
  },
  google: {
    models: ["gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"],
    api_key_prefix: "AI"
  },
  groq: {
    models: ["meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct"],
    api_key_prefix: "gsk_"
  },
  openrouter: {
    models: ["google/gemini-2.5-flash", "anthropic/claude-opus-4.5", "x-ai/grok-4.1-fast", "openai/gpt-oss-120b", "minimax/minimax-m2.1", "google/gemini-2.5-flash-lite", "openai/gpt-5.2", "anthropic/claude-3.5-sonnet"],
    api_key_prefix: "sk-or-"
  }
}

// Fixed for now: Gemini only
const FIXED_PROVIDER = "google"
const FIXED_MODEL = "gemini-2.5-flash"

const LLMSettings: React.FC<LLMSettingsProps> = ({ isOpen, onClose, userId, onApiKeySaved }) => {
  const { isLightMode } = useTheme()
  const [provider] = useState<string>(FIXED_PROVIDER)
  const [model] = useState<string>(FIXED_MODEL)
  const [apiKey, setApiKey] = useState<string>("")
  const [showApiKey, setShowApiKey] = useState<boolean>(false)
  const [currentConfig, setCurrentConfig] = useState<LLMConfig | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isSaving, setIsSaving] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Load current configuration
  useEffect(() => {
    if (isOpen && userId) {
      loadCurrentConfig()
    }
  }, [isOpen, userId])

  const loadCurrentConfig = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_URL}${API_ENDPOINTS.LLM_CONFIG}?user_id=${userId}`)
      if (response.ok) {
        const config: LLMConfig = await response.json()
        setCurrentConfig(config)
        // Provider/model are fixed (Gemini); only API key state is used from config
        // Don't set API key (security - it's not returned)
      } else {
        setError("Failed to load current configuration")
      }
    } catch (err) {
      setError("Error loading configuration")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const saveConfiguration = async () => {
    if (!provider || !model) {
      setError("Please select provider and model")
      return
    }

    setIsSaving(true)
    setError(null)

    try {
      const response = await fetch(`${API_URL}${API_ENDPOINTS.LLM_CONFIG}?user_id=${userId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          provider,
          model,
          api_key: apiKey || undefined, // Only send if provided - backend will reuse existing if available
        }),
      })

      if (response.ok) {
        // Reload current config
        await loadCurrentConfig()
        // Clear API key field for security
        setApiKey("")
        // Notify parent to refresh API key state
        if (onApiKeySaved) {
          onApiKeySaved()
        }
        // Close modal after a short delay
        setTimeout(() => {
          onClose()
        }, 1000)
      } else {
        const data = await response.json()
        // Show error message from backend (e.g., "API key is required when switching to provider X")
        setError(data.detail?.message || "Failed to save configuration")
      }
    } catch (err) {
      setError("Error saving configuration")
      console.error(err)
    } finally {
      setIsSaving(false)
    }
  }

  const providerInfo = AVAILABLE_PROVIDERS[provider as keyof typeof AVAILABLE_PROVIDERS]

  if (!isOpen) return null

  const modalContent = (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: isLightMode ? "rgba(0, 0, 0, 0.4)" : "rgba(0, 0, 0, 0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        backdropFilter: "blur(4px)",
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: "var(--bg-panel)",
          borderRadius: 16,
          padding: 24,
          width: "90%",
          maxWidth: 600,
          maxHeight: "90vh",
          overflow: "auto",
          border: "1px solid var(--border-light)",
          boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600, color: "var(--text-primary)" }}>LLM Settings</h2>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: "var(--text-tertiary)",
              padding: 4,
              transition: "color 0.2s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "var(--text-primary)"
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "var(--text-tertiary)"
            }}
          >
            <X size={20} />
          </button>
        </div>

        {isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
            <Loader className="animate-spin" size={24} color="var(--accent-primary)" />
          </div>
        ) : (
          <>
            {/* Fixed: Gemini provider & model (read-only) */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", marginBottom: 8, fontSize: 14, fontWeight: 500, color: "var(--text-primary)" }}>
                Provider
              </label>
              <div
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: "1px solid var(--border-light)",
                  backgroundColor: "var(--bg-input)",
                  color: "var(--text-tertiary)",
                  fontSize: 14,
                }}
              >
                Gemini
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", marginBottom: 8, fontSize: 14, fontWeight: 500, color: "var(--text-primary)" }}>
                Model
              </label>
              <div
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: "1px solid var(--border-light)",
                  backgroundColor: "var(--bg-input)",
                  color: "var(--text-tertiary)",
                  fontSize: 14,
                }}
              >
                gemini-2.5-flash
              </div>
            </div>

            {/* API Key Input */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", marginBottom: 8, fontSize: 14, fontWeight: 500, color: "var(--text-primary)" }}>
                API Key
                {providerInfo && (
                  <span style={{ fontSize: 12, color: "var(--text-tertiary)", marginLeft: 8 }}>
                    (starts with {providerInfo.api_key_prefix}...)
                  </span>
                )}
                {currentConfig && currentConfig.has_api_key && currentConfig.provider === provider && (
                  <span style={{ fontSize: 12, color: "var(--accent-primary)", marginLeft: 8 }}>
                    (optional - click Save to reuse existing key)
                  </span>
                )}
                {currentConfig && currentConfig.has_api_key && currentConfig.provider !== provider && (
                  <span style={{ fontSize: 12, color: "#fbbf24", marginLeft: 8 }}>
                    (required - different provider needs new key)
                  </span>
                )}
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type={showApiKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    currentConfig && currentConfig.has_api_key && currentConfig.provider === provider
                      ? "Leave empty to reuse existing API key, or enter new key to update"
                      : "Enter your API key"
                  }
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    paddingRight: 40,
                    borderRadius: 8,
                    border: "1px solid var(--border-light)",
                    backgroundColor: "var(--bg-input)",
                    color: "var(--text-primary)",
                    fontSize: 14,
                  }}
                />
                <button
                  onClick={() => setShowApiKey(!showApiKey)}
                  style={{
                    position: "absolute",
                    right: 8,
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--text-tertiary)",
                    padding: 4,
                    transition: "color 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = "var(--text-primary)"
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = "var(--text-tertiary)"
                  }}
                >
                  {showApiKey ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Current Configuration Info */}
            {currentConfig && currentConfig.has_api_key && (
              <div
                style={{
                  padding: 12,
                  borderRadius: 8,
                  backgroundColor: "var(--accent-primary-bg)",
                  border: "1px solid var(--accent-primary-border)",
                  marginBottom: 20,
                }}
              >
                <div style={{ fontSize: 12, color: "var(--accent-primary)" }}>
                  Current: {currentConfig.provider}/{currentConfig.model}
                  {currentConfig.updated_at && (
                    <span style={{ marginLeft: 8, opacity: 0.7 }}>
                      (Updated: {new Date(currentConfig.updated_at).toLocaleDateString()})
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div
                style={{
                  padding: 12,
                  borderRadius: 8,
                  backgroundColor: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid rgba(239, 68, 68, 0.2)",
                  marginBottom: 20,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <AlertCircle size={16} color="#ef4444" />
                <span style={{ fontSize: 12, color: "#ef4444" }}>{error}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button
                onClick={saveConfiguration}
                disabled={isSaving || !provider || !model}
                style={{
                  padding: "10px 20px",
                  borderRadius: 8,
                  border: "none",
                  background: "linear-gradient(135deg, #003323, #50D387)",
                  color: "#fff",
                  cursor: isSaving || !provider || !model ? "not-allowed" : "pointer",
                  opacity: isSaving || !provider || !model ? 0.5 : 1,
                  fontSize: 14,
                  fontWeight: 500,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  transition: "opacity 0.2s ease",
                }}
              >
                {isSaving ? (
                  <>
                    <Loader className="animate-spin" size={16} />
                    Saving...
                  </>
                ) : (
                  "Save"
                )}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )

  // Render modal using portal to ensure it's at the root level
  return createPortal(modalContent, document.body)
}

export default LLMSettings
