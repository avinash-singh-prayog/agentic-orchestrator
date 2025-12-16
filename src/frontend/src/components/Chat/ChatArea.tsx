/**
 * Chat Area Component
 * 
 * Premium styled chat interface with proper streaming and sync support.
 */

import React, { useState, useRef, useEffect } from "react"
import { Send, Loader2, Sparkles } from "lucide-react"
import { v4 as uuidv4 } from "uuid"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import { useStreamingActions, useStreamingStatus, useStreamingFinalResponse, useStreamingEvents } from "@/stores/orchestratorStreamingStore"
import StreamingFeed from "./StreamingFeed"
import type { Message } from "@/types/message"
import { EXAMPLE_PROMPTS } from "@/utils/const"

interface ChatAreaProps {
    onAgentActive?: (agent: string | null) => void
}

const ChatArea: React.FC<ChatAreaProps> = ({ onAgentActive }) => {
    const [input, setInput] = useState("")
    const [messages, setMessages] = useState<Message[]>([])
    const [useStreaming, setUseStreaming] = useState(true)
    const inputRef = useRef<HTMLInputElement>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const { sendMessage, loading: apiLoading } = useAgentAPI()
    const { startStreaming, reset } = useStreamingActions()
    const streamingStatus = useStreamingStatus()
    const finalResponse = useStreamingFinalResponse()
    const streamingEvents = useStreamingEvents()

    const isLoading = apiLoading || streamingStatus === "streaming" || streamingStatus === "connecting"
    const isStreamActive = streamingStatus !== "idle"

    // Scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, streamingStatus, finalResponse, streamingEvents])

    // Add final streaming response as assistant message when complete
    useEffect(() => {
        if (streamingStatus === "completed" && finalResponse && useStreaming) {
            const assistantMessage: Message = {
                id: uuidv4(),
                role: "assistant",
                content: finalResponse,
                timestamp: new Date(),
            }
            setMessages((prev) => {
                const lastMsg = prev[prev.length - 1]
                if (lastMsg?.role === "assistant" && lastMsg?.content === finalResponse) {
                    return prev
                }
                return [...prev, assistantMessage]
            })
        }
    }, [streamingStatus, finalResponse, useStreaming])

    // Create final message from last streaming event if no explicit final response
    useEffect(() => {
        if (streamingStatus === "completed" && !finalResponse && streamingEvents.length > 0 && useStreaming) {
            const lastEvent = streamingEvents[streamingEvents.length - 1]
            const assistantMessage: Message = {
                id: uuidv4(),
                role: "assistant",
                content: lastEvent.message,
                timestamp: new Date(),
            }
            setMessages((prev) => {
                const lastMsg = prev[prev.length - 1]
                if (lastMsg?.role === "assistant") {
                    return prev
                }
                return [...prev, assistantMessage]
            })
        }
    }, [streamingStatus, finalResponse, streamingEvents, useStreaming])

    const handleSend = async () => {
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: uuidv4(),
            role: "user",
            content: input.trim(),
            timestamp: new Date(),
        }

        setMessages((prev) => [...prev, userMessage])
        const prompt = input.trim()
        setInput("")
        reset()

        if (useStreaming) {
            await startStreaming(prompt)
        } else {
            // Sync mode - show animation for Supervisor during processing
            onAgentActive?.("Supervisor")
            try {
                const response = await sendMessage(prompt)
                if (response) {
                    const assistantMessage: Message = {
                        id: uuidv4(),
                        role: "assistant",
                        content: response,
                        timestamp: new Date(),
                    }
                    setMessages((prev) => [...prev, assistantMessage])
                }
            } catch (err) {
                console.error("Send error:", err)
                const errorMessage: Message = {
                    id: uuidv4(),
                    role: "assistant",
                    content: "Sorry, an error occurred. Please try again.",
                    timestamp: new Date(),
                }
                setMessages((prev) => [...prev, errorMessage])
            } finally {
                onAgentActive?.(null)
            }
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const containerStyles: React.CSSProperties = {
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "linear-gradient(180deg, #14161e 0%, #1a1d28 100%)",
    }

    const headerStyles: React.CSSProperties = {
        padding: "16px 20px",
        borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
    }

    const exampleButtonStyles: React.CSSProperties = {
        width: "100%",
        padding: "12px 16px",
        textAlign: "left",
        fontSize: 13,
        color: "#d1dae8",
        background: "rgba(35, 39, 56, 0.6)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        borderRadius: 12,
        cursor: "pointer",
        transition: "all 0.2s ease",
    }

    const inputStyles: React.CSSProperties = {
        flex: 1,
        padding: "14px 48px 14px 16px",
        fontSize: 14,
        color: "#f8fafc",
        background: "rgba(35, 39, 56, 0.8)",
        border: "1px solid rgba(255, 255, 255, 0.12)",
        borderRadius: 14,
        outline: "none",
    }

    const sendButtonStyles: React.CSSProperties = {
        position: "absolute",
        right: 8,
        top: "50%",
        transform: "translateY(-50%)",
        width: 36,
        height: 36,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 10,
        background: "linear-gradient(135deg, #4f8fff, #9d7cf6)",
        border: "none",
        cursor: input.trim() && !isLoading ? "pointer" : "not-allowed",
        opacity: input.trim() && !isLoading ? 1 : 0.5,
    }

    const showEmptyState = messages.length === 0 && !isStreamActive

    return (
        <div style={containerStyles}>
            {/* Header */}
            <div style={headerStyles}>
                <h2 style={{ fontSize: 15, fontWeight: 600, color: "#f1f5f9", marginBottom: 2 }}>Chat</h2>
                <p style={{ fontSize: 12, color: "#64748b" }}>Ask about shipping routes, rates, or bookings</p>
            </div>

            {/* Messages */}
            <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
                {showEmptyState ? (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", textAlign: "center", paddingInline: 16 }}>
                        <div style={{
                            width: 64,
                            height: 64,
                            borderRadius: 20,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: "linear-gradient(135deg, rgba(79, 143, 255, 0.15), rgba(157, 124, 246, 0.15))",
                            border: "1px solid rgba(255, 255, 255, 0.12)",
                            marginBottom: 20,
                        }}>
                            <Sparkles style={{ width: 32, height: 32, color: "#6ba6ff" }} />
                        </div>
                        <h2 style={{ fontSize: 18, fontWeight: 600, color: "#f8fafc", marginBottom: 8 }}>How can I help?</h2>
                        <p style={{ fontSize: 13, color: "#a8b5cf", marginBottom: 24, maxWidth: 280, lineHeight: 1.5 }}>
                            I coordinate with specialized agents to help with shipping logistics.
                        </p>

                        <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%" }}>
                            {EXAMPLE_PROMPTS.slice(0, 4).map((prompt, i) => (
                                <button key={i} style={exampleButtonStyles} onClick={() => { setInput(prompt); inputRef.current?.focus() }}>
                                    {prompt}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                        {messages.map((msg) => (
                            <div key={msg.id} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }} className="message-appear">
                                <div style={{
                                    maxWidth: "85%",
                                    padding: "12px 16px",
                                    borderRadius: msg.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                                    background: msg.role === "user"
                                        ? "linear-gradient(135deg, #4f8fff, #9d7cf6)"
                                        : "rgba(35, 39, 56, 0.9)",
                                    border: msg.role === "user" ? "none" : "1px solid rgba(255, 255, 255, 0.12)",
                                    color: "#f8fafc",
                                }}>
                                    <p style={{ fontSize: 14, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>{msg.content}</p>
                                </div>
                            </div>
                        ))}

                        {/* Streaming feed - show during active streaming */}
                        {useStreaming && isStreamActive && streamingStatus !== "completed" && <StreamingFeed />}

                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input area */}
            <div style={{ padding: 16, borderTop: "1px solid rgba(255, 255, 255, 0.1)", background: "rgba(20, 22, 30, 0.9)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <button
                        onClick={() => setUseStreaming(!useStreaming)}
                        style={{
                            padding: "8px 12px",
                            fontSize: 12,
                            fontWeight: 500,
                            borderRadius: 8,
                            border: useStreaming ? "1px solid rgba(79, 143, 255, 0.4)" : "1px solid rgba(255, 255, 255, 0.12)",
                            background: useStreaming ? "rgba(79, 143, 255, 0.15)" : "rgba(35, 39, 56, 0.6)",
                            color: useStreaming ? "#6ba6ff" : "#a8b5cf",
                            cursor: "pointer",
                        }}
                    >
                        {useStreaming ? "Stream" : "Sync"}
                    </button>

                    <div style={{ flex: 1, position: "relative" }}>
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Type your message..."
                            style={inputStyles}
                            disabled={isLoading}
                        />
                        <button onClick={handleSend} disabled={!input.trim() || isLoading} style={sendButtonStyles}>
                            {isLoading ? (
                                <Loader2 style={{ width: 16, height: 16, color: "white", animation: "spin 1s linear infinite" }} />
                            ) : (
                                <Send style={{ width: 16, height: 16, color: "white" }} />
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ChatArea
