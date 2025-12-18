/**
 * Chat Area Component
 * 
 * Premium styled chat interface with proper streaming and sync support.
 * Syncs with chatHistoryStore for conversation persistence.
 */

import React, { useState, useRef, useEffect } from "react"
import { Send, Loader2, Sparkles } from "lucide-react"
import { v4 as uuidv4 } from "uuid"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import { useStreamingActions, useStreamingStatus, useStreamingFinalResponse, useStreamingEvents } from "@/stores/orchestratorStreamingStore"
import { useChatMessages, useActiveConversationId } from "@/stores/chatHistoryStore"
import ExecutionTimeline from "./ExecutionTimeline"
import type { Message } from "@/types/message"
import { EXAMPLE_PROMPTS } from "@/utils/const"

interface ChatAreaProps {
    onAgentActive?: (agent: string | null) => void
}

const ChatArea: React.FC<ChatAreaProps> = () => {
    const [input, setInput] = useState("")
    const [messages, setMessages] = useState<Message[]>([])
    const inputRef = useRef<HTMLInputElement>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const { loading: apiLoading } = useAgentAPI()
    const { startStreaming, reset } = useStreamingActions()
    const streamingStatus = useStreamingStatus()
    const finalResponse = useStreamingFinalResponse()
    const streamingEvents = useStreamingEvents()

    // Get messages from chat history store
    const historyMessages = useChatMessages()
    const activeConversationId = useActiveConversationId()

    const isLoading = apiLoading || streamingStatus === "streaming" || streamingStatus === "connecting"
    const isStreamActive = streamingStatus === "streaming" || streamingStatus === "connecting"

    // Sync local messages with history store when active conversation changes
    useEffect(() => {
        if (activeConversationId && historyMessages.length > 0) {
            // Convert history messages to local format
            const convertedMessages: Message[] = historyMessages.map(msg => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                timestamp: new Date(msg.timestamp),
                activity: msg.activity
            }))
            setMessages(convertedMessages)
        } else {
            // Clear messages when no active conversation OR new/empty conversation
            setMessages([])
        }
    }, [activeConversationId, historyMessages])

    // Scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, streamingStatus, finalResponse, streamingEvents])

    // Add final streaming response as assistant message when complete
    useEffect(() => {
        if (streamingStatus === "completed" && finalResponse) {
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
    }, [streamingStatus, finalResponse])

    // Create final message from last streaming event if no explicit final response
    useEffect(() => {
        if (streamingStatus === "completed" && !finalResponse && streamingEvents.length > 0) {
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
    }, [streamingStatus, finalResponse, streamingEvents])

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

        await startStreaming(prompt)
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
        background: "var(--bg-app)",
    }

    const headerStyles: React.CSSProperties = {
        padding: "16px 20px",
        borderBottom: "1px solid var(--border-subtle)",
    }

    const exampleButtonStyles: React.CSSProperties = {
        width: "100%",
        padding: "12px 16px",
        textAlign: "left",
        fontSize: 13,
        color: "var(--text-secondary)",
        background: "var(--bg-card)",
        border: "1px solid var(--border-light)",
        borderRadius: 12,
        cursor: "pointer",
        transition: "all 0.2s ease",
    }

    const inputStyles: React.CSSProperties = {
        flex: 1,
        padding: "14px 48px 14px 16px",
        fontSize: 14,
        color: "var(--text-primary)",
        background: "var(--bg-input)",
        border: "1px solid var(--border-light)",
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
        background: "linear-gradient(135deg, var(--color-blue-500), var(--color-purple-500))",
        border: "none",
        cursor: input.trim() && !isLoading ? "pointer" : "not-allowed",
        opacity: input.trim() && !isLoading ? 1 : 0.5,
    }

    const showEmptyState = messages.length === 0 && !isStreamActive

    return (
        <div style={containerStyles}>
            {/* Header */}
            <div style={headerStyles}>
                <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>Chat</h2>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Ask about shipping routes, rates, or bookings</p>
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
                            background: "var(--accent-primary-bg)",
                            border: "1px solid var(--border-light)",
                            marginBottom: 20,
                        }}>
                            <Sparkles style={{ width: 32, height: 32, color: "var(--accent-primary)" }} />
                        </div>
                        <h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>How can I help?</h2>
                        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 24, maxWidth: 280, lineHeight: 1.5 }}>
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
                            <React.Fragment key={msg.id}>
                                {/* Show stored activity BEFORE assistant message (that generated it) */}
                                {msg.role === 'assistant' && msg.activity && msg.activity.length > 0 && (
                                    <ExecutionTimeline
                                        events={msg.activity}
                                        isLive={false}
                                        defaultCollapsed={true}
                                    />
                                )}

                                <div style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }} className="message-appear">
                                    <div style={{
                                        maxWidth: "85%",
                                        padding: "12px 16px",
                                        borderRadius: msg.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                                        background: msg.role === "user"
                                            ? "linear-gradient(135deg, var(--color-blue-500), var(--color-purple-500))"
                                            : "var(--bg-card)",
                                        border: msg.role === "user" ? "none" : "1px solid var(--border-light)",
                                        color: "#f8fafc", // Keep white text on colored bubbles
                                    }}>
                                        <p style={{
                                            fontSize: 14,
                                            lineHeight: 1.5,
                                            whiteSpace: "pre-wrap",
                                            color: msg.role === "user" ? "#f8fafc" : "var(--text-primary)"
                                        }}>{msg.content}</p>
                                    </div>
                                </div>
                            </React.Fragment>
                        ))}

                        {/* Live Agent Activity - shows during streaming */}
                        {isStreamActive && <ExecutionTimeline isLive={true} />}

                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input area */}
            <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border-subtle)", background: "var(--bg-panel)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ flex: 1, position: "relative" }}>
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Type your message..."
                            style={{ ...inputStyles, width: "100%" }}
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
