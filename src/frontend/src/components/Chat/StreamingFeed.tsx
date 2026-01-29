/**
 * Streaming Feed Component
 * 
 * Real-time display of agent events with inline styles.
 */

import React from "react"
import { Brain, MapPin, CircleDollarSign, Package, Zap, CheckCircle, AlertCircle, Loader2, ArrowRight } from "lucide-react"
import ReactMarkdown from "react-markdown"
import {
    useStreamingEvents,
    useStreamingStatus,
    useStreamingFinalResponse,
} from "@/stores/orchestratorStreamingStore"

const agentIcons: Record<string, React.FC<{ style?: React.CSSProperties }>> = {
    supervisor: Brain,
    serviceability: MapPin,
    rate: CircleDollarSign,
    carrier: Package,
    slim: Zap,
}

const agentColors: Record<string, { gradient: string; text: string }> = {
    supervisor: { gradient: "linear-gradient(135deg, #003323, #50D387)", text: "#50D387" },
    serviceability: { gradient: "linear-gradient(135deg, #003323, #50D387)", text: "#50D387" },
    rate: { gradient: "linear-gradient(135deg, #003323, #50D387)", text: "#50D387" },
    carrier: { gradient: "linear-gradient(135deg, #003323, #50D387)", text: "#50D387" },
    slim: { gradient: "linear-gradient(135deg, #50D387, #80e0a8)", text: "#50D387" },
}

const StreamingFeed: React.FC = () => {
    const events = useStreamingEvents()
    const status = useStreamingStatus()
    const finalResponse = useStreamingFinalResponse()

    if (status === "idle") return null

    const cardStyles: React.CSSProperties = {
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        padding: 16,
        borderRadius: 14,
        background: "rgba(35, 39, 56, 0.8)",
        border: "1px solid rgba(255, 255, 255, 0.12)",
    }

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Connecting */}
            {status === "connecting" && (
                <div style={{ ...cardStyles }} className="fade-in-up">
                    <Loader2 style={{ width: 18, height: 18, color: "#50D387", animation: "spin 1s linear infinite" }} />
                    <span style={{ fontSize: 13, color: "#a8b5cf" }}>Connecting to orchestrator...</span>
                </div>
            )}

            {/* Events */}
            {events.map((event, index) => {
                const senderKey = event.sender.toLowerCase()
                const Icon = agentIcons[senderKey] || Brain
                const colors = agentColors[senderKey] || agentColors.supervisor
                const isLatest = index === events.length - 1

                return (
                    <div
                        key={index}
                        style={{
                            ...cardStyles,
                            border: isLatest && event.state !== "COMPLETED"
                                ? "1px solid rgba(80, 211, 135, 0.4)"
                                : "1px solid rgba(255, 255, 255, 0.12)",
                            boxShadow: isLatest && event.state !== "COMPLETED"
                                ? "0 4px 20px rgba(80, 211, 135, 0.2)"
                                : "none",
                        }}
                        className="fade-in-up"
                    >
                        {/* Icon */}
                        <div style={{
                            width: 36,
                            height: 36,
                            borderRadius: 10,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: colors.gradient,
                            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
                            flexShrink: 0,
                        }}>
                            <Icon style={{ width: 18, height: 18, color: "white" }} />
                        </div>

                        {/* Content */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: colors.text, textTransform: "capitalize" }}>
                                    {event.sender}
                                </span>
                                {event.receiver && (
                                    <>
                                        <ArrowRight style={{ width: 12, height: 12, color: "#8b9cb8" }} />
                                        <span style={{ fontSize: 11, color: "#8b9cb8" }}>{event.receiver}</span>
                                    </>
                                )}
                                {isLatest && event.state !== "COMPLETED" && (
                                    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
                                        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#50D387", animation: "pulse 2s infinite" }} />
                                        <span style={{ fontSize: 10, color: "#50D387", textTransform: "uppercase", letterSpacing: 1 }}>Processing</span>
                                    </div>
                                )}
                                {event.state === "COMPLETED" && (
                                    <CheckCircle style={{ marginLeft: "auto", width: 16, height: 16, color: "#22c997" }} />
                                )}
                            </div>
                            <div style={{ fontSize: 13, color: "#e8eef7", lineHeight: 1.5 }}>
                                <ReactMarkdown
                                    components={{
                                        p: ({ children }) => <p style={{ margin: "0 0 8px 0" }}>{children}</p>,
                                        strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                                        em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
                                        ul: ({ children }) => <ul style={{ margin: "8px 0", paddingLeft: "20px" }}>{children}</ul>,
                                        ol: ({ children }) => <ol style={{ margin: "8px 0", paddingLeft: "20px" }}>{children}</ol>,
                                        li: ({ children }) => <li style={{ margin: "4px 0" }}>{children}</li>,
                                        h1: ({ children }) => <h1 style={{ fontSize: 16, fontWeight: 600, margin: "12px 0 8px 0" }}>{children}</h1>,
                                        h2: ({ children }) => <h2 style={{ fontSize: 15, fontWeight: 600, margin: "10px 0 6px 0" }}>{children}</h2>,
                                        h3: ({ children }) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: "8px 0 4px 0" }}>{children}</h3>,
                                        code: ({ children, className }) => {
                                            const isInline = !className
                                            return isInline ? (
                                                <code style={{
                                                    background: "rgba(0, 0, 0, 0.3)",
                                                    padding: "2px 6px",
                                                    borderRadius: 4,
                                                    fontSize: "0.9em",
                                                    fontFamily: "monospace"
                                                }}>{children}</code>
                                            ) : (
                                                <code style={{
                                                    display: "block",
                                                    background: "rgba(0, 0, 0, 0.3)",
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
                                                borderLeft: "3px solid rgba(255, 255, 255, 0.2)",
                                                paddingLeft: "12px",
                                                margin: "8px 0",
                                                fontStyle: "italic"
                                            }}>{children}</blockquote>
                                        ),
                                        hr: () => <hr style={{ border: "none", borderTop: "1px solid rgba(255, 255, 255, 0.15)", margin: "12px 0" }} />,
                                    }}
                                >
                                    {event.message}
                                </ReactMarkdown>
                            </div>
                        </div>
                    </div>
                )
            })}

            {/* Final response */}
            {finalResponse && status === "completed" && (
                <div style={{
                    ...cardStyles,
                    background: "rgba(34, 201, 151, 0.12)",
                    border: "1px solid rgba(34, 201, 151, 0.35)",
                }} className="fade-in-up">
                    <div style={{
                        width: 28,
                        height: 28,
                        borderRadius: 8,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: "#22c997",
                    }}>
                        <CheckCircle style={{ width: 16, height: 16, color: "white" }} />
                    </div>
                    <div>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#3ee8c6", display: "block", marginBottom: 6 }}>
                            Complete
                        </span>
                        <div style={{ fontSize: 13, color: "#e8eef7", lineHeight: 1.5 }}>
                            <ReactMarkdown
                                components={{
                                    p: ({ children }) => <p style={{ margin: "0 0 8px 0" }}>{children}</p>,
                                    strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                                    em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
                                    ul: ({ children }) => <ul style={{ margin: "8px 0", paddingLeft: "20px" }}>{children}</ul>,
                                    ol: ({ children }) => <ol style={{ margin: "8px 0", paddingLeft: "20px" }}>{children}</ol>,
                                    li: ({ children }) => <li style={{ margin: "4px 0" }}>{children}</li>,
                                    h1: ({ children }) => <h1 style={{ fontSize: 16, fontWeight: 600, margin: "12px 0 8px 0" }}>{children}</h1>,
                                    h2: ({ children }) => <h2 style={{ fontSize: 15, fontWeight: 600, margin: "10px 0 6px 0" }}>{children}</h2>,
                                    h3: ({ children }) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: "8px 0 4px 0" }}>{children}</h3>,
                                    code: ({ children, className }) => {
                                        const isInline = !className
                                        return isInline ? (
                                            <code style={{
                                                background: "rgba(0, 0, 0, 0.3)",
                                                padding: "2px 6px",
                                                borderRadius: 4,
                                                fontSize: "0.9em",
                                                fontFamily: "monospace"
                                            }}>{children}</code>
                                        ) : (
                                            <code style={{
                                                display: "block",
                                                background: "rgba(0, 0, 0, 0.3)",
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
                                            borderLeft: "3px solid rgba(255, 255, 255, 0.2)",
                                            paddingLeft: "12px",
                                            margin: "8px 0",
                                            fontStyle: "italic"
                                        }}>{children}</blockquote>
                                    ),
                                    hr: () => <hr style={{ border: "none", borderTop: "1px solid rgba(255, 255, 255, 0.15)", margin: "12px 0" }} />,
                                }}
                            >
                                {finalResponse}
                            </ReactMarkdown>
                        </div>
                    </div>
                </div>
            )}

            {/* Error */}
            {status === "error" && (
                <div style={{
                    ...cardStyles,
                    background: "rgba(248, 113, 113, 0.12)",
                    border: "1px solid rgba(248, 113, 113, 0.35)",
                }} className="fade-in-up">
                    <AlertCircle style={{ width: 18, height: 18, color: "#f87171" }} />
                    <span style={{ fontSize: 13, fontWeight: 500, color: "#fca5a5" }}>
                        An error occurred while processing your request.
                    </span>
                </div>
            )}
        </div>
    )
}

export default StreamingFeed
