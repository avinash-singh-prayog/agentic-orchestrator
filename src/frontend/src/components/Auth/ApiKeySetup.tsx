/**
 * API Key Setup Component
 * 
 * Modal component that prompts users to configure their API key.
 * Can be dismissed and shown again when needed.
 */

import React, { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { API_ENDPOINTS } from '@/utils/const'
import axios from 'axios'
import { Loader2, Key, Eye, EyeOff, CheckCircle, AlertCircle, ArrowRight, X } from 'lucide-react'

const API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL
if (!API_URL) {
    throw new Error('VITE_ORCHESTRATOR_API_URL is not defined')
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
        models: ["meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct", "llama-3.3-70b-scout", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        api_key_prefix: "gsk_"
    },
    openrouter: {
        models: ["google/gemini-2.5-flash", "anthropic/claude-opus-4.5", "x-ai/grok-4.1-fast", "openai/gpt-oss-120b", "minimax/minimax-m2.1", "google/gemini-2.5-flash-lite", "openai/gpt-5.2", "anthropic/claude-3.5-sonnet"],
        api_key_prefix: "sk-or-"
    }
}

interface ApiKeySetupProps {
    userId: string
    isOpen: boolean
    onClose: () => void
    onComplete: () => void
}

const ApiKeySetup: React.FC<ApiKeySetupProps> = ({ userId, isOpen, onClose, onComplete }) => {
    const [provider, setProvider] = useState<string>("openai")
    const [model, setModel] = useState<string>("")
    const [apiKey, setApiKey] = useState<string>("")
    const [showApiKey, setShowApiKey] = useState<boolean>(false)
    const [isSaving, setIsSaving] = useState<boolean>(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<boolean>(false)

    // Update models when provider changes
    useEffect(() => {
        if (provider && AVAILABLE_PROVIDERS[provider as keyof typeof AVAILABLE_PROVIDERS]) {
            const models = AVAILABLE_PROVIDERS[provider as keyof typeof AVAILABLE_PROVIDERS].models
            if (models.length > 0) {
                setModel(models[0])
            }
        }
    }, [provider])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        
        if (!provider || !model || !apiKey.trim()) {
            setError("Please select a provider, model, and enter your API key")
            return
        }

        setIsSaving(true)
        setError(null)

        try {
            const response = await axios.post(
                `${API_URL}${API_ENDPOINTS.LLM_CONFIG}?user_id=${userId}`,
                {
                    provider,
                    model,
                    api_key: apiKey.trim()
                }
            )

            if (response.status === 200) {
                setSuccess(true)
                // Wait a moment to show success message, then call onComplete and close
                // onComplete will update the store to mark API key as configured
                setTimeout(() => {
                    onComplete()
                    onClose()
                }, 1500)
            }
        } catch (err: any) {
            console.error("API key setup error:", err)
            const msg = err.response?.data?.detail
                ? (typeof err.response.data.detail === 'string' 
                    ? err.response.data.detail 
                    : err.response.data.detail.message)
                : err.message || "Failed to save API key configuration"
            setError(msg)
        } finally {
            setIsSaving(false)
        }
    }

    const providerInfo = AVAILABLE_PROVIDERS[provider as keyof typeof AVAILABLE_PROVIDERS]
    const models = providerInfo?.models || []

    if (!isOpen) return null

    const notificationContent = (
        <div
            style={{
                position: "fixed",
                top: 80,
                right: 24,
                zIndex: 9999,
                maxWidth: 420,
                animation: "slideInRight 0.3s ease-out",
            }}
        >
            <style>{`
                @keyframes slideInRight {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            `}</style>
            <div
                className="bg-[var(--bg-panel)] border border-[var(--border-subtle)] rounded-2xl shadow-2xl p-6 relative backdrop-blur-xl transition-colors duration-300"
                style={{
                    boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
                }}
            >
                {/* Close Button */}
                <button
                    onClick={onClose}
                    style={{
                        position: "absolute",
                        top: 12,
                        right: 12,
                        background: "transparent",
                        border: "none",
                        cursor: "pointer",
                        color: "var(--text-tertiary)",
                        padding: 4,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        borderRadius: 8,
                        transition: "all 0.2s ease",
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = "var(--bg-app)"
                        e.currentTarget.style.color = "var(--text-primary)"
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = "transparent"
                        e.currentTarget.style.color = "var(--text-tertiary)"
                    }}
                    title="Close"
                >
                    <X size={18} />
                </button>
                {/* Header */}
                <div className="mb-6">
                    <div className="flex items-start gap-3 mb-4">
                        <div className="p-2 bg-[var(--accent-primary)]/10 rounded-lg flex-shrink-0">
                            <Key className="text-[var(--accent-primary)]" size={20} />
                        </div>
                        <div className="flex-1">
                            <h2 className="text-lg font-bold text-[var(--text-primary)] mb-1">
                                Configure API Key
                            </h2>
                            <p className="text-[var(--text-secondary)] text-sm">
                                Set up your LLM API key to start chatting
                            </p>
                        </div>
                    </div>
                </div>

                {/* Success Message */}
                {success && (
                    <div className="mb-4 p-3 bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/20 rounded-lg flex items-center gap-2 text-[var(--accent-primary)] text-sm">
                        <CheckCircle size={16} />
                        <span>API key configured successfully!</span>
                    </div>
                )}

                {/* Error Message */}
                {error && (
                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-500 text-sm">
                        <AlertCircle size={16} />
                        <span>{error}</span>
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Provider Selection */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                            Provider
                        </label>
                        <select
                            value={provider}
                            onChange={(e) => setProvider(e.target.value)}
                            className="w-full bg-[var(--bg-app)] border border-[var(--border-light)] rounded-lg py-2.5 px-3 outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)] transition-all text-sm text-[var(--text-primary)]"
                            required
                        >
                            {Object.keys(AVAILABLE_PROVIDERS).map((p) => (
                                <option key={p} value={p}>
                                    {p.charAt(0).toUpperCase() + p.slice(1)}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Model Selection */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                            Model
                        </label>
                        <select
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className="w-full bg-[var(--bg-app)] border border-[var(--border-light)] rounded-lg py-2.5 px-3 outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)] transition-all text-sm text-[var(--text-primary)]"
                            required
                        >
                            {models.map((m) => (
                                <option key={m} value={m}>
                                    {m}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* API Key Input */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                            API Key
                            {providerInfo && (
                                <span className="text-[var(--text-tertiary)] font-normal normal-case ml-2">
                                    (starts with {providerInfo.api_key_prefix}...)
                                </span>
                            )}
                        </label>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]" size={16} />
                            <input
                                type={showApiKey ? "text" : "password"}
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                                placeholder="Enter your API key"
                                className="w-full bg-[var(--bg-app)] border border-[var(--border-light)] rounded-lg py-2.5 pl-9 pr-9 outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)] transition-all text-sm text-[var(--text-primary)]"
                                required
                                minLength={10}
                            />
                            <button
                                type="button"
                                onClick={() => setShowApiKey(!showApiKey)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
                            >
                                {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={isSaving || success || !provider || !model || !apiKey.trim()}
                        className="w-full bg-gradient-to-r from-[#003323] to-[var(--accent-primary)] hover:from-[#004d2e] hover:to-[#80e0a8] text-white font-medium py-2.5 rounded-lg flex items-center justify-center gap-2 transition-all transform active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed mt-2 shadow-lg shadow-[var(--accent-primary)]/20 text-sm"
                    >
                        {isSaving ? (
                            <>
                                <Loader2 className="animate-spin" size={16} />
                                <span>Saving...</span>
                            </>
                        ) : success ? (
                            <>
                                <CheckCircle size={16} />
                                <span>Success!</span>
                            </>
                        ) : (
                            <>
                                <span>Save</span>
                                <ArrowRight size={14} />
                            </>
                        )}
                    </button>
                </form>

                {/* Help Text */}
                <div className="mt-4 text-center text-xs text-[var(--text-tertiary)]">
                    <p>
                        Need an API key?{' '}
                        {provider === 'openai' && <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-[var(--text-accent)] hover:opacity-80">OpenAI</a>}
                        {provider === 'anthropic' && <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-[var(--text-accent)] hover:opacity-80">Anthropic</a>}
                        {provider === 'google' && <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-[var(--text-accent)] hover:opacity-80">Google AI Studio</a>}
                        {provider === 'groq' && <a href="https://console.groq.com/keys" target="_blank" rel="noopener noreferrer" className="text-[var(--text-accent)] hover:opacity-80">Groq</a>}
                        {provider === 'openrouter' && <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="text-[var(--text-accent)] hover:opacity-80">OpenRouter</a>}
                    </p>
                </div>
            </div>
        </div>
    )

    return createPortal(notificationContent, document.body)
}

export default ApiKeySetup
