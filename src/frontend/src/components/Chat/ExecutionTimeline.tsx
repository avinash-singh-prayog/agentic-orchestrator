/**
 * Execution Timeline Component
 * 
 * Vertical timeline showing agent activity.
 * - Supports LIVE mode (from streaming store) and STORED mode (from props)
 * - Collapsible: entire timeline can collapse to summary
 * - Expandable steps: click to see full message
 */

import React, { useState, useMemo } from "react"
import {
    Brain,
    MapPin,
    CircleDollarSign,
    Package,
    Zap,
    CheckCircle2,
    XCircle,
    Loader2,
    ChevronDown,
    ChevronUp,
    Activity,
    ShoppingCart
} from "lucide-react"
import {
    useStreamingEvents,
    useStreamingStatus,
} from "@/stores/orchestratorStreamingStore"

// ============================================================================
// Types
// ============================================================================

export interface AgentEvent {
    sender: string
    receiver?: string
    message: string
    state?: string
}

interface ExecutionTimelineProps {
    events?: AgentEvent[]  // If provided, use these (stored mode)
    isLive?: boolean       // If true, use streaming store (live mode)
    defaultCollapsed?: boolean
}

// ============================================================================
// Agent Configuration
// ============================================================================

const agentConfig: Record<string, {
    icon: React.FC<{ style?: React.CSSProperties }>
    color: string
    bgColor: string
    label: string
}> = {
    supervisor: {
        icon: Brain,
        color: "#6ba6ff",
        bgColor: "rgba(107, 166, 255, 0.15)",
        label: "Supervisor Agent"
    },
    serviceability: {
        icon: MapPin,
        color: "#22d3ee",
        bgColor: "rgba(34, 211, 238, 0.15)",
        label: "Serviceability Agent"
    },
    booking: {
        icon: ShoppingCart,
        color: "#f472b6",
        bgColor: "rgba(244, 114, 182, 0.15)",
        label: "Booking Agent"
    },
    rate: {
        icon: CircleDollarSign,
        color: "#fbbf24",
        bgColor: "rgba(251, 191, 36, 0.15)",
        label: "Rate Agent"
    },
    carrier: {
        icon: Package,
        color: "#34d399",
        bgColor: "rgba(52, 211, 153, 0.15)",
        label: "Serviceability Agent"
    },
    slim: {
        icon: Zap,
        color: "#a78bfa",
        bgColor: "rgba(167, 139, 250, 0.15)",
        label: "SLIM Transport"
    },
}

// ============================================================================
// Component
// ============================================================================

const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({
    events: propsEvents,
    isLive = true,
    defaultCollapsed = false
}) => {
    // Live streaming data (only used when isLive=true)
    const streamingEvents = useStreamingEvents()
    const streamingStatus = useStreamingStatus()

    // Use props events if provided, otherwise use streaming events
    const events = propsEvents ?? (isLive ? streamingEvents : [])
    const status = isLive ? streamingStatus : "completed"

    const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed)
    const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())

    // Calculate execution stats
    const stats = useMemo(() => {
        const stepCount = events.length
        return { stepCount }
    }, [events])

    // Don't render if no events
    if (events.length === 0 && !isLive) return null
    if (isLive && status === "idle" && events.length === 0) return null

    const toggleStep = (index: number) => {
        setExpandedSteps(prev => {
            const next = new Set(prev)
            if (next.has(index)) next.delete(index)
            else next.add(index)
            return next
        })
    }

    const getStatusIcon = (isActive: boolean, isCompleted: boolean) => {
        if (isActive) return <Loader2 style={{ width: 14, height: 14, color: "#6ba6ff", animation: "spin 1s linear infinite" }} />
        if (isCompleted) return <CheckCircle2 style={{ width: 14, height: 14, color: "#22c997" }} />
        return null
    }

    // ============================================================================
    // Styles
    // ============================================================================

    const containerStyles: React.CSSProperties = {
        background: "rgba(20, 22, 30, 0.95)",
        borderRadius: 12,
        border: "1px solid rgba(255, 255, 255, 0.1)",
        overflow: "hidden",
        marginBottom: 12,
    }

    const headerStyles: React.CSSProperties = {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 14px",
        background: "rgba(255, 255, 255, 0.03)",
        borderBottom: isCollapsed ? "none" : "1px solid rgba(255, 255, 255, 0.08)",
        cursor: "pointer",
        userSelect: "none",
    }

    const timelineStyles: React.CSSProperties = {
        padding: isCollapsed ? 0 : "12px 14px",
        maxHeight: isCollapsed ? 0 : 250,
        overflow: isCollapsed ? "hidden" : "auto",
        transition: "all 0.3s ease",
    }

    const stepStyles = (config: typeof agentConfig.supervisor, isActive: boolean): React.CSSProperties => ({
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        padding: "6px 0",
        marginLeft: 8,
        borderLeft: `2px solid ${isActive ? config.color : "rgba(255, 255, 255, 0.1)"}`,
        position: "relative",
    })

    const nodeStyles = (config: typeof agentConfig.supervisor): React.CSSProperties => ({
        position: "absolute",
        left: -5,
        top: 8,
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: config.color,
    })

    // ============================================================================
    // Render
    // ============================================================================

    return (
        <div style={containerStyles}>
            {/* Header */}
            <div style={headerStyles} onClick={() => setIsCollapsed(!isCollapsed)}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Activity style={{ width: 14, height: 14, color: "#a8b5cf" }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0" }}>
                        Agent Activity
                    </span>
                    {stats.stepCount > 0 && (
                        <span style={{
                            fontSize: 10,
                            color: "#64748b",
                            background: "rgba(255, 255, 255, 0.08)",
                            padding: "2px 6px",
                            borderRadius: 8,
                        }}>
                            {stats.stepCount} steps
                        </span>
                    )}
                </div>

                {/* Status & Toggle */}
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {isLive && (status === "streaming" || status === "connecting") ? (
                        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <div style={{
                                width: 6,
                                height: 6,
                                borderRadius: "50%",
                                background: "#6ba6ff",
                                animation: "pulse 1.5s infinite"
                            }} />
                            <span style={{ fontSize: 10, color: "#6ba6ff" }}>Running</span>
                        </div>
                    ) : status === "completed" || !isLive ? (
                        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <CheckCircle2 style={{ width: 12, height: 12, color: "#22c997" }} />
                            <span style={{ fontSize: 10, color: "#22c997" }}>Done</span>
                        </div>
                    ) : status === "error" ? (
                        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <XCircle style={{ width: 12, height: 12, color: "#ef4444" }} />
                            <span style={{ fontSize: 10, color: "#ef4444" }}>Error</span>
                        </div>
                    ) : null}

                    {isCollapsed ? (
                        <ChevronDown style={{ width: 14, height: 14, color: "#64748b" }} />
                    ) : (
                        <ChevronUp style={{ width: 14, height: 14, color: "#64748b" }} />
                    )}
                </div>
            </div>

            {/* Timeline */}
            <div style={timelineStyles}>
                {events.map((event, index) => {
                    const getAgentKey = (sender: string) => {
                        const s = sender.toLowerCase()
                        if (s.includes("carrier")) return "carrier"
                        if (s.includes("rate")) return "rate"
                        if (s.includes("service")) return "serviceability"
                        if (s.includes("booking")) return "booking"
                        if (s.includes("slim")) return "slim"
                        return "supervisor"
                    }
                    const senderKey = getAgentKey(event.sender)
                    const config = agentConfig[senderKey] || agentConfig.supervisor
                    const Icon = config.icon
                    const isLatest = index === events.length - 1
                    const isActive = isLive && isLatest && (status === "streaming" || status === "connecting")
                    const isExpanded = expandedSteps.has(index)

                    return (
                        <div key={index} style={stepStyles(config, isActive)}>
                            {/* Node */}
                            <div style={nodeStyles(config)} />

                            {/* Content */}
                            <div style={{ flex: 1, paddingLeft: 8 }}>
                                <div
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 6,
                                        cursor: "pointer",
                                    }}
                                    onClick={() => toggleStep(index)}
                                >
                                    {/* Agent icon */}
                                    <div style={{
                                        width: 20,
                                        height: 20,
                                        borderRadius: 5,
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        background: config.bgColor,
                                    }}>
                                        <Icon style={{ width: 10, height: 10, color: config.color }} />
                                    </div>

                                    {/* Agent name */}
                                    <span style={{ fontSize: 11, fontWeight: 500, color: config.color }}>
                                        {config.label}
                                    </span>

                                    {/* Status */}
                                    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
                                        {getStatusIcon(isActive, event.state === "COMPLETED" || !isLive)}
                                        {isExpanded ? (
                                            <ChevronUp style={{ width: 12, height: 12, color: "#64748b" }} />
                                        ) : (
                                            <ChevronDown style={{ width: 12, height: 12, color: "#64748b" }} />
                                        )}
                                    </div>
                                </div>

                                {/* Message - truncated or full */}
                                <p style={{
                                    fontSize: 11,
                                    color: "#94a3b8",
                                    marginTop: 2,
                                    lineHeight: 1.4,
                                    ...(isExpanded ? {} : {
                                        overflow: "hidden",
                                        textOverflow: "ellipsis",
                                        whiteSpace: "nowrap",
                                        maxWidth: "90%",
                                    })
                                }}>
                                    {event.message}
                                </p>

                                {/* Expanded details */}
                                {isExpanded && (
                                    <div style={{
                                        marginTop: 6,
                                        padding: 8,
                                        background: "rgba(255, 255, 255, 0.03)",
                                        borderRadius: 6,
                                        border: "1px solid rgba(255, 255, 255, 0.06)",
                                        fontSize: 10,
                                    }}>
                                        {event.receiver && (
                                            <div style={{ color: "#64748b", marginBottom: 2 }}>
                                                <strong style={{ color: "#94a3b8" }}>Target:</strong> {event.receiver}
                                            </div>
                                        )}
                                        <div style={{ color: "#94a3b8" }}>
                                            <strong>Message:</strong>
                                            <p style={{
                                                marginTop: 2,
                                                padding: 6,
                                                background: "rgba(0,0,0,0.2)",
                                                borderRadius: 4,
                                                whiteSpace: "pre-wrap",
                                                wordBreak: "break-word",
                                            }}>
                                                {event.message}
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

export default ExecutionTimeline
