/**
 * Chat Area Component
 * 
 * Premium styled chat interface with proper streaming and sync support.
 * Syncs with chatHistoryStore for conversation persistence.
 */

import React, { useState, useRef, useEffect } from "react"
import { Send, Sparkles, Square, FileText, Image as ImageIcon, X } from "lucide-react"
import { v4 as uuidv4 } from "uuid"
import ReactMarkdown from "react-markdown"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import { useStreamingActions, useStreamingStatus, useStreamingFinalResponse, useStreamingEvents, useStreamingError } from "@/stores/orchestratorStreamingStore"
import { useChatMessages, useActiveConversationId } from "@/stores/chatHistoryStore"
import ExecutionTimeline from "./ExecutionTimeline"
import FileUpload from "./FileUpload"
import type { Message, FileAttachment } from "@/types/message"
import { EXAMPLE_PROMPTS } from "@/utils/const"

interface ChatAreaProps {
    onAgentActive?: (agent: string | null) => void
}

const ChatArea: React.FC<ChatAreaProps> = () => {
    const [input, setInput] = useState("")
    const [messages, setMessages] = useState<Message[]>([])
    const [selectedFiles, setSelectedFiles] = useState<FileAttachment[]>([])
    const inputRef = useRef<HTMLTextAreaElement>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const { loading: apiLoading } = useAgentAPI()
    const { startStreaming, stopStreaming, reset } = useStreamingActions()
    const streamingStatus = useStreamingStatus()
    const finalResponse = useStreamingFinalResponse()
    const streamingEvents = useStreamingEvents()

    // Get messages from chat history store
    const historyMessages = useChatMessages()
    const activeConversationId = useActiveConversationId()
    const streamingError = useStreamingError()

    const isLoading = apiLoading || streamingStatus === "streaming" || streamingStatus === "connecting"
    const isStreamActive = streamingStatus === "streaming" || streamingStatus === "connecting"

    // Display streaming errors in chat
    useEffect(() => {
        if (streamingError && streamingStatus === "error") {
            const errorMessage: Message = {
                id: uuidv4(),
                role: "assistant",
                content: streamingError,
                timestamp: new Date(),
            }
            setMessages((prev) => {
                // Don't add duplicate error messages
                const lastMsg = prev[prev.length - 1]
                if (lastMsg?.role === "assistant" && lastMsg?.content === streamingError) {
                    return prev
                }
                return [...prev, errorMessage]
            })
        }
    }, [streamingError, streamingStatus])

    // Sync local messages with history store when active conversation changes
    useEffect(() => {
        if (activeConversationId && historyMessages.length > 0) {
            // Convert history messages to local format
            const convertedMessages: Message[] = historyMessages.map(msg => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                timestamp: new Date(msg.timestamp),
                activity: msg.activity,
                attachments: msg.attachments
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
        if ((!input.trim() && selectedFiles.length === 0) || isLoading) return

        // Filter out files without file object
        const validFiles = selectedFiles.filter(f => f.file)
        
        if (selectedFiles.length > 0 && validFiles.length === 0) {
            // All files failed to process
            alert("Failed to process files. Please try again or use different files.")
            return
        }

        const userMessage: Message = {
            id: uuidv4(),
            role: "user",
            content: input.trim() || (validFiles.length > 0 ? `[Attached ${validFiles.length} file(s)]` : ""),
            timestamp: new Date(),
            attachments: validFiles.length > 0 ? [...validFiles] : undefined,
        }

        setMessages((prev) => [...prev, userMessage])
        const prompt = input.trim()
        const attachments = validFiles.length > 0 ? [...validFiles] : undefined
        setInput("")
        setSelectedFiles([])

        // Reset height
        if (inputRef.current) {
            inputRef.current.style.height = 'auto'
        }

        reset()
        // Let backend handle API key validation - errors will be displayed via streaming error state
        await startStreaming(prompt, {}, attachments)
    }

    const handleFilesSelected = (attachments: FileAttachment[]) => {
        setSelectedFiles((prev) => {
            const newFiles = [...prev, ...attachments]
            // Limit to max files
            return newFiles.slice(0, 5)
        })
    }

    const handleFilesRemoved = (attachmentIds: string[]) => {
        setSelectedFiles((prev) => prev.filter((f) => !attachmentIds.includes(f.id)))
    }

    const handleStop = () => {
        stopStreaming()
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value)

        // Auto-resize
        if (inputRef.current) {
            inputRef.current.style.height = 'auto'
            inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`
        }
    }

    const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
        e.preventDefault()
        const text = e.clipboardData.getData("text/plain")
        // Normalize newlines: limit consecutive newlines to 2, trim start/end
        const normalized = text.replace(/\n{3,}/g, "\n\n").trim()

        const newValue = input + normalized
        setInput(newValue)

        // Trigger resize after state update
        setTimeout(() => {
            if (inputRef.current) {
                inputRef.current.style.height = 'auto'
                inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`
            }
        }, 0)
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
        background: "var(--bg-panel)",
        border: "1px solid var(--border-light)",
        borderRadius: 12,
        cursor: "pointer",
        transition: "all 0.2s ease",
    }


    const showEmptyState = messages.length === 0 && !isStreamActive

    return (
        <div style={containerStyles}>
            {/* Header */}
            <div style={headerStyles}>
                <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>Chat</h2>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Ask about transaction analysis or root cause analysis</p>
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
                            I help analyze transaction failures and perform root cause analysis.
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
                                            ? "linear-gradient(135deg, #003323, #50D387)"
                                            : "var(--bg-panel)",
                                        border: msg.role === "user" ? "none" : "1px solid var(--border-light)",
                                        color: "#f8fafc", // Keep white text on colored bubbles
                                    }}>
                                        {/* Show attachments if present */}
                                        {msg.attachments && msg.attachments.length > 0 && (
                                            <div style={{
                                                marginBottom: msg.content ? 12 : 0,
                                                display: "flex",
                                                flexDirection: "column",
                                                gap: 8,
                                            }}>
                                                {msg.attachments.map((attachment) => (
                                                    <div
                                                        key={attachment.id}
                                                        style={{
                                                            display: "flex",
                                                            alignItems: "center",
                                                            gap: 8,
                                                            padding: "8px 12px",
                                                            background: msg.role === "user" 
                                                                ? "rgba(255, 255, 255, 0.15)" 
                                                                : "var(--bg-input)",
                                                            borderRadius: 8,
                                                            fontSize: 13,
                                                        }}
                                                    >
                                                        {attachment.fileType === "image" ? (
                                                            <ImageIcon style={{ width: 16, height: 16, color: msg.role === "user" ? "#f8fafc" : "var(--text-primary)" }} />
                                                        ) : (
                                                            <FileText style={{ width: 16, height: 16, color: msg.role === "user" ? "#f8fafc" : "var(--text-primary)" }} />
                                                        )}
                                                        <span style={{
                                                            flex: 1,
                                                            overflow: "hidden",
                                                            textOverflow: "ellipsis",
                                                            whiteSpace: "nowrap",
                                                            color: msg.role === "user" ? "#f8fafc" : "var(--text-primary)",
                                                        }}>
                                                            {attachment.name}
                                                        </span>
                                                        {attachment.url && attachment.fileType === "image" && (
                                                            <img
                                                                src={attachment.url}
                                                                alt={attachment.name}
                                                                style={{
                                                                    maxWidth: 100,
                                                                    maxHeight: 100,
                                                                    borderRadius: 4,
                                                                    objectFit: "cover",
                                                                }}
                                                            />
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        <div style={{
                                            fontSize: 14,
                                            lineHeight: 1.5,
                                            color: msg.role === "user" ? "#f8fafc" : "var(--text-primary)"
                                        }}>
                                            <ReactMarkdown
                                                components={{
                                                    p: ({ children }) => <p style={{ margin: "0 0 8px 0" }}>{children}</p>,
                                                    strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                                                    em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
                                                    ul: ({ children }) => <ul style={{ margin: "8px 0", paddingLeft: "20px" }}>{children}</ul>,
                                                    ol: ({ children }) => <ol style={{ margin: "8px 0", paddingLeft: "20px" }}>{children}</ol>,
                                                    li: ({ children }) => <li style={{ margin: "4px 0" }}>{children}</li>,
                                                    h1: ({ children }) => <h1 style={{ fontSize: 18, fontWeight: 600, margin: "12px 0 8px 0" }}>{children}</h1>,
                                                    h2: ({ children }) => <h2 style={{ fontSize: 16, fontWeight: 600, margin: "10px 0 6px 0" }}>{children}</h2>,
                                                    h3: ({ children }) => <h3 style={{ fontSize: 15, fontWeight: 600, margin: "8px 0 4px 0" }}>{children}</h3>,
                                                    code: ({ children, className }) => {
                                                        const isInline = !className
                                                        return isInline ? (
                                                            <code style={{
                                                                background: msg.role === "user" ? "rgba(0, 0, 0, 0.2)" : "rgba(0, 0, 0, 0.15)",
                                                                padding: "2px 6px",
                                                                borderRadius: 4,
                                                                fontSize: "0.9em",
                                                                fontFamily: "monospace"
                                                            }}>{children}</code>
                                                        ) : (
                                                            <code style={{
                                                                display: "block",
                                                                background: msg.role === "user" ? "rgba(0, 0, 0, 0.2)" : "rgba(0, 0, 0, 0.15)",
                                                                padding: "8px 12px",
                                                                borderRadius: 6,
                                                                fontSize: "0.9em",
                                                                fontFamily: "monospace",
                                                                overflow: "auto",
                                                                margin: "8px 0"
                                                            }}>{children}</code>
                                                        )
                                                    },
                                                    blockquote: ({ children }) => (
                                                        <blockquote style={{
                                                            borderLeft: `3px solid ${msg.role === "user" ? "rgba(255, 255, 255, 0.3)" : "var(--border-light)"}`,
                                                            paddingLeft: "12px",
                                                            margin: "8px 0",
                                                            fontStyle: "italic"
                                                        }}>{children}</blockquote>
                                                    ),
                                                    hr: () => <hr style={{ border: "none", borderTop: `1px solid ${msg.role === "user" ? "rgba(255, 255, 255, 0.2)" : "var(--border-light)"}`, margin: "12px 0" }} />,
                                                }}
                                            >
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    </div>
                                </div>
                            </React.Fragment>
                        ))}

                        {/* Live Agent Activity - shows during streaming */}
                        {isStreamActive && <ExecutionTimeline isLive={true} defaultCollapsed={true} />}

                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input area */}
            <div style={{ padding: "20px", background: "var(--bg-app)" }}>
                <div style={{ 
                    position: "relative",
                    background: "var(--bg-input)",
                    border: "1px solid var(--border-light)",
                    borderRadius: 16,
                    padding: selectedFiles.length > 0 ? "12px 12px 12px 16px" : "12px 12px 12px 16px",
                    minHeight: 56,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8
                }}>
                    {/* File previews inside input area */}
                    {selectedFiles.length > 0 && (
                        <div style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 6,
                            marginBottom: 4
                        }}>
                            {selectedFiles.map((attachment) => (
                                <div
                                    key={attachment.id}
                                    style={{
                                        position: "relative",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: 8,
                                        padding: "8px 28px 8px 12px",
                                        background: "var(--bg-panel)",
                                        border: "1px solid var(--border-light)",
                                        borderRadius: 8,
                                        fontSize: 13,
                                        maxWidth: "fit-content",
                                    }}
                                >
                                    {attachment.fileType === "image" ? (
                                        <ImageIcon style={{ width: 18, height: 18, color: "var(--text-primary)", flexShrink: 0 }} />
                                    ) : (
                                        <FileText style={{ width: 18, height: 18, color: "var(--text-primary)", flexShrink: 0 }} />
                                    )}
                                    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                                        <span
                                            style={{
                                                maxWidth: "150px",
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                                color: "var(--text-primary)",
                                                fontSize: 13,
                                            }}
                                            title={attachment.name}
                                        >
                                            {attachment.name}
                                        </span>
                                        <span style={{ color: "var(--text-secondary)", fontSize: 11 }}>
                                            {attachment.fileType === "image" ? "Image" : "Spreadsheet"}
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => handleFilesRemoved([attachment.id])}
                                        style={{
                                            position: "absolute",
                                            top: -6,
                                            right: -6,
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "center",
                                            width: 20,
                                            height: 20,
                                            padding: 0,
                                            background: "var(--bg-app)",
                                            border: "1px solid var(--border-light)",
                                            cursor: "pointer",
                                            color: "var(--text-secondary)",
                                            borderRadius: "50%",
                                            boxShadow: "0 2px 4px rgba(0, 0, 0, 0.1)",
                                        }}
                                        title="Remove file"
                                    >
                                        <X style={{ width: 12, height: 12 }} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    <div style={{ display: "flex", alignItems: "center", gap: 12, position: "relative", paddingRight: 0 }}>
                        <FileUpload
                            onFilesSelected={handleFilesSelected}
                            onFilesRemoved={handleFilesRemoved}
                            selectedFiles={selectedFiles}
                            maxFiles={5}
                            disabled={isLoading}
                        />
                        <textarea
                            ref={inputRef as any}
                            value={input}
                            onChange={handleInput}
                            onPaste={handlePaste}
                            onKeyDown={handleKeyPress}
                            placeholder="Ask anything"
                            rows={1}
                            style={{
                                flex: 1,
                                fontSize: 14,
                                color: "var(--text-primary)",
                                background: "transparent",
                                border: "none",
                                outline: "none",
                                resize: "none",
                                minHeight: 24,
                                maxHeight: 120,
                                padding: 0,
                                paddingRight: 48,
                                fontFamily: "inherit",
                                lineHeight: 1.5,
                            }}
                            disabled={isLoading}
                        />

                        {isLoading ? (
                            <button onClick={handleStop} style={{
                                position: "absolute",
                                right: 0,
                                top: "50%",
                                transform: "translateY(-50%)",
                                width: 36,
                                height: 36,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                borderRadius: "50%",
                                background: "var(--bg-panel)",
                                border: "1px solid var(--border-light)",
                                cursor: "pointer",
                                opacity: 1
                            }} title="Stop generating">
                                <Square style={{ width: 10, height: 10, fill: "#ef4444", color: "#ef4444" }} />
                            </button>
                        ) : (
                            <button 
                                type="button"
                                onClick={handleSend} 
                                disabled={(!input.trim() && selectedFiles.length === 0) || isLoading} 
                                style={{
                                    position: "absolute",
                                    right: 0,
                                    top: "50%",
                                    transform: "translateY(-50%)",
                                    width: 36,
                                    height: 36,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    borderRadius: "50%",
                                    background: (input.trim() || selectedFiles.length > 0) && !isLoading
                                        ? "linear-gradient(135deg, #003323, #50D387)" 
                                        : "var(--bg-panel)",
                                    border: "none",
                                    cursor: (input.trim() || selectedFiles.length > 0) && !isLoading ? "pointer" : "not-allowed",
                                    opacity: (input.trim() || selectedFiles.length > 0) && !isLoading ? 1 : 0.5,
                                    transition: "all 0.2s ease",
                                }}
                                title="Send message"
                            >
                                <Send style={{ width: 16, height: 16, color: "white" }} />
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ChatArea
