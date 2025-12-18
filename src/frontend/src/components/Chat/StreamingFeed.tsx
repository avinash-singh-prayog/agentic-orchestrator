/**
 * Streaming Feed Component
 * 
 * Real-time display of agent events with inline styles.
 */

import React from "react"
import { Brain, MapPin, CircleDollarSign, Package, Zap, CheckCircle, AlertCircle, Loader2, ArrowRight } from "lucide-react"
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
    supervisor: { gradient: "linear-gradient(135deg, #4f8fff, #9d7cf6)", text: "#6ba6ff" },
    serviceability: { gradient: "linear-gradient(135deg, #22c997, #2dd4bf)", text: "#3ee8c6" },
    rate: { gradient: "linear-gradient(135deg, #fbbf24, #fb923c)", text: "#fcd34d" },
    carrier: { gradient: "linear-gradient(135deg, #9d7cf6, #f472b6)", text: "#c4b5fd" },
    slim: { gradient: "linear-gradient(135deg, #22d3ee, #4f8fff)", text: "#38d9f5" },
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
                    <Loader2 style={{ width: 18, height: 18, color: "#6ba6ff", animation: "spin 1s linear infinite" }} />
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
                                ? "1px solid rgba(79, 143, 255, 0.4)"
                                : "1px solid rgba(255, 255, 255, 0.12)",
                            boxShadow: isLatest && event.state !== "COMPLETED"
                                ? "0 4px 20px rgba(79, 143, 255, 0.2)"
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
                                        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#4f8fff", animation: "pulse 2s infinite" }} />
                                        <span style={{ fontSize: 10, color: "#6ba6ff", textTransform: "uppercase", letterSpacing: 1 }}>Processing</span>
                                    </div>
                                )}
                                {event.state === "COMPLETED" && (
                                    <CheckCircle style={{ marginLeft: "auto", width: 16, height: 16, color: "#22c997" }} />
                                )}
                            </div>
                            <p style={{ fontSize: 13, color: "#e8eef7", lineHeight: 1.5 }}>{event.message}</p>
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
                        <p style={{ fontSize: 13, color: "#e8eef7", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                            {finalResponse}
                        </p>
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
