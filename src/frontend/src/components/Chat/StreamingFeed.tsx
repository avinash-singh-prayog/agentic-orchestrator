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
    supervisor: { gradient: "linear-gradient(135deg, #3b82f6, #8b5cf6)", text: "#60a5fa" },
    serviceability: { gradient: "linear-gradient(135deg, #10b981, #14b8a6)", text: "#34d399" },
    rate: { gradient: "linear-gradient(135deg, #f59e0b, #f97316)", text: "#fbbf24" },
    carrier: { gradient: "linear-gradient(135deg, #8b5cf6, #ec4899)", text: "#a78bfa" },
    slim: { gradient: "linear-gradient(135deg, #06b6d4, #3b82f6)", text: "#22d3ee" },
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
        background: "rgba(30, 32, 48, 0.8)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
    }

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Connecting */}
            {status === "connecting" && (
                <div style={{ ...cardStyles }} className="fade-in-up">
                    <Loader2 style={{ width: 18, height: 18, color: "#60a5fa", animation: "spin 1s linear infinite" }} />
                    <span style={{ fontSize: 13, color: "#94a3b8" }}>Connecting to orchestrator...</span>
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
                                ? "1px solid rgba(59, 130, 246, 0.4)"
                                : "1px solid rgba(255, 255, 255, 0.1)",
                            boxShadow: isLatest && event.state !== "COMPLETED"
                                ? "0 4px 20px rgba(59, 130, 246, 0.15)"
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
                            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.2)",
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
                                        <ArrowRight style={{ width: 12, height: 12, color: "#64748b" }} />
                                        <span style={{ fontSize: 11, color: "#64748b" }}>{event.receiver}</span>
                                    </>
                                )}
                                {isLatest && event.state !== "COMPLETED" && (
                                    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
                                        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#3b82f6", animation: "pulse 2s infinite" }} />
                                        <span style={{ fontSize: 10, color: "#60a5fa", textTransform: "uppercase", letterSpacing: 1 }}>Processing</span>
                                    </div>
                                )}
                                {event.state === "COMPLETED" && (
                                    <CheckCircle style={{ marginLeft: "auto", width: 16, height: 16, color: "#10b981" }} />
                                )}
                            </div>
                            <p style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.5 }}>{event.message}</p>
                        </div>
                    </div>
                )
            })}

            {/* Final response */}
            {finalResponse && status === "completed" && (
                <div style={{
                    ...cardStyles,
                    background: "rgba(16, 185, 129, 0.1)",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                }} className="fade-in-up">
                    <div style={{
                        width: 28,
                        height: 28,
                        borderRadius: 8,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: "#10b981",
                    }}>
                        <CheckCircle style={{ width: 16, height: 16, color: "white" }} />
                    </div>
                    <div>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#34d399", display: "block", marginBottom: 6 }}>
                            Complete
                        </span>
                        <p style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                            {finalResponse}
                        </p>
                    </div>
                </div>
            )}

            {/* Error */}
            {status === "error" && (
                <div style={{
                    ...cardStyles,
                    background: "rgba(239, 68, 68, 0.1)",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                }} className="fade-in-up">
                    <AlertCircle style={{ width: 18, height: 18, color: "#ef4444" }} />
                    <span style={{ fontSize: 13, fontWeight: 500, color: "#f87171" }}>
                        An error occurred while processing your request.
                    </span>
                </div>
            )}
        </div>
    )
}

export default StreamingFeed
