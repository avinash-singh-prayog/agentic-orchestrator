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
    ShoppingCart,
    FileSearch
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import {
    useStreamingEvents,
    useStreamingStatus,
} from "@/stores/orchestratorStreamingStore"
import { useTheme } from "@/contexts/ThemeContext"

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
        color: "#50D387",
        bgColor: "rgba(80, 211, 135, 0.15)",
        label: "Supervisor Agent"
    },
    serviceability: {
        icon: MapPin,
        color: "#50D387",
        bgColor: "rgba(80, 211, 135, 0.15)",
        label: "Serviceability Agent"
    },
    booking: {
        icon: ShoppingCart,
        color: "#50D387",
        bgColor: "rgba(80, 211, 135, 0.15)",
        label: "Booking Agent"
    },
    "transaction-rca": {
        icon: FileSearch,
        color: "#50D387",
        bgColor: "rgba(80, 211, 135, 0.15)",
        label: "Transaction RCA Agent"
    },
    "external-db": {
        icon: FileSearch,
        color: "#50D387",
        bgColor: "rgba(80, 211, 135, 0.15)",
        label: "RCA agent"
    },
    rate: {
        icon: CircleDollarSign,
        color: "#50D387",
        bgColor: "rgba(80, 211, 135, 0.15)",
        label: "Rate Agent"
    },
    carrier: {
        icon: Package,
        color: "#50D387",
        bgColor: "rgba(80, 211, 135, 0.15)",
        label: "Serviceability Agent"
    },
    slim: {
        icon: Zap,
        color: "#50D387",
        bgColor: "rgba(80, 211, 135, 0.15)",
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
    const { isLightMode } = useTheme()

    // Use props events if provided, otherwise use streaming events
    const events = propsEvents ?? (isLive ? streamingEvents : [])
    const status = isLive ? streamingStatus : "completed"

    const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed)
    const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())

    // Sync collapsed state when defaultCollapsed prop changes
    React.useEffect(() => {
        setIsCollapsed(defaultCollapsed)
    }, [defaultCollapsed])

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
        background: isLightMode ? "rgba(255, 255, 255, 0.9)" : "rgba(20, 22, 30, 0.95)",
        borderRadius: 12,
        border: isLightMode ? "1px solid rgba(0, 0, 0, 0.1)" : "1px solid rgba(255, 255, 255, 0.1)",
        overflow: "hidden",
        marginBottom: 12,
    }

    const headerStyles: React.CSSProperties = {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 14px",
        background: isLightMode ? "rgba(241, 245, 249, 0.8)" : "rgba(255, 255, 255, 0.03)",
        borderBottom: isCollapsed ? "none" : (isLightMode ? "1px solid rgba(0, 0, 0, 0.08)" : "1px solid rgba(255, 255, 255, 0.08)"),
        cursor: "pointer",
        userSelect: "none",
    }

    const timelineStyles: React.CSSProperties = {
        padding: isCollapsed ? 0 : "12px 14px",
        maxHeight: isCollapsed ? 0 : "none", // Remove height limit when expanded
        overflow: isCollapsed ? "hidden" : "visible", // Allow overflow when expanded
        transition: "all 0.3s ease",
    }

    const stepStyles = (config: typeof agentConfig.supervisor, isActive: boolean): React.CSSProperties => ({
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        padding: "6px 0",
        marginLeft: 8,
        borderLeft: `2px solid ${isActive ? config.color : (isLightMode ? "rgba(0, 0, 0, 0.1)" : "rgba(255, 255, 255, 0.1)")}`,
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
                    <Activity style={{ width: 14, height: 14, color: isLightMode ? "#64748b" : "#a8b5cf" }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: isLightMode ? "#1e293b" : "#e2e8f0" }}>
                        Agent Activity
                    </span>
                    {stats.stepCount > 0 && (
                        <span style={{
                            fontSize: 10,
                            color: isLightMode ? "#475569" : "#64748b",
                            background: isLightMode ? "rgba(0, 0, 0, 0.05)" : "rgba(255, 255, 255, 0.08)",
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
                        <ChevronDown style={{ width: 14, height: 14, color: isLightMode ? "#64748b" : "#64748b" }} />
                    ) : (
                        <ChevronUp style={{ width: 14, height: 14, color: isLightMode ? "#64748b" : "#64748b" }} />
                    )}
                </div>
            </div>

            {/* Timeline */}
            <div style={timelineStyles}>
                {events.map((event, index) => {
                    const getAgentKey = (sender: string) => {
                        const s = sender.toLowerCase()
                        if (s.includes("external") && s.includes("db")) return "external-db"
                        if (s.includes("carrier")) return "carrier"
                        if (s.includes("transaction") && s.includes("rca")) return "transaction-rca"
                        if (s.includes("rca")) return "transaction-rca"
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
                                            <ChevronUp style={{ width: 12, height: 12, color: isLightMode ? "#64748b" : "#64748b" }} />
                                        ) : (
                                            <ChevronDown style={{ width: 12, height: 12, color: isLightMode ? "#64748b" : "#64748b" }} />
                                        )}
                                    </div>
                                </div>

                                {/* Message - truncated or full */}
                                <div style={{
                                    fontSize: 11,
                                    color: isLightMode ? "#475569" : "#94a3b8",
                                    marginTop: 2,
                                    lineHeight: 1.4,
                                    ...(isExpanded ? {} : {
                                        overflow: "hidden",
                                        textOverflow: "ellipsis",
                                        wordBreak: "break-word",
                                        // maxWidth: "90%", // Let it take available space
                                    })
                                }}>
                                    <ReactMarkdown
                                        components={{
                                            p: ({ children }) => <p style={{ margin: "0 0 4px 0" }}>{children}</p>,
                                            strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                                            em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
                                            ul: ({ children }) => <ul style={{ margin: "4px 0", paddingLeft: "16px" }}>{children}</ul>,
                                            ol: ({ children }) => <ol style={{ margin: "4px 0", paddingLeft: "16px" }}>{children}</ol>,
                                            li: ({ children }) => <li style={{ margin: "2px 0" }}>{children}</li>,
                                            code: ({ children, className }) => {
                                                const isInline = !className
                                                return isInline ? (
                                                    <code style={{
                                                        background: isLightMode ? "rgba(0, 0, 0, 0.05)" : "rgba(0, 0, 0, 0.3)",
                                                        padding: "1px 4px",
                                                        borderRadius: 3,
                                                        fontSize: "0.9em",
                                                        fontFamily: "monospace"
                                                    }}>{children}</code>
                                                ) : (
                                                    <code style={{
                                                        display: "block",
                                                        background: isLightMode ? "rgba(0, 0, 0, 0.05)" : "rgba(0, 0, 0, 0.3)",
                                                        padding: "6px 8px",
                                                        borderRadius: 4,
                                                        fontSize: "0.9em",
                                                        fontFamily: "monospace",
                                                        overflow: "auto",
                                                        margin: "4px 0"
                                                    }}>{children}</code>
                                                )
                                            },
                                        }}
                                    >
                                        {event.message}
                                    </ReactMarkdown>
                                </div>

                                {/* Expanded details */}
                                {isExpanded && (
                                    <div style={{
                                        marginTop: 6,
                                        padding: 8,
                                        background: isLightMode ? "rgba(241, 245, 249, 0.8)" : "rgba(255, 255, 255, 0.03)",
                                        borderRadius: 6,
                                        border: isLightMode ? "1px solid rgba(0, 0, 0, 0.08)" : "1px solid rgba(255, 255, 255, 0.06)",
                                        fontSize: 10,
                                    }}>
                                        {event.receiver && (
                                            <div style={{ color: isLightMode ? "#64748b" : "#64748b", marginBottom: 2 }}>
                                                <strong style={{ color: isLightMode ? "#475569" : "#94a3b8" }}>Target:</strong> {event.receiver}
                                            </div>
                                        )}
                                        <div style={{ color: isLightMode ? "#475569" : "#94a3b8" }}>
                                            <strong>Message:</strong>
                                            <div style={{
                                                marginTop: 2,
                                                padding: 6,
                                                background: isLightMode ? "rgba(0, 0, 0, 0.03)" : "rgba(0,0,0,0.2)",
                                                borderRadius: 4,
                                                wordBreak: "break-word",
                                            }}>
                                                <ReactMarkdown
                                                    components={{
                                                        p: ({ children }) => <p style={{ margin: "0 0 4px 0" }}>{children}</p>,
                                                        strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                                                        em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
                                                        ul: ({ children }) => <ul style={{ margin: "4px 0", paddingLeft: "16px" }}>{children}</ul>,
                                                        ol: ({ children }) => <ol style={{ margin: "4px 0", paddingLeft: "16px" }}>{children}</ol>,
                                                        li: ({ children }) => <li style={{ margin: "2px 0" }}>{children}</li>,
                                                        code: ({ children, className }) => {
                                                            const isInline = !className
                                                            return isInline ? (
                                                                <code style={{
                                                                    background: isLightMode ? "rgba(0, 0, 0, 0.05)" : "rgba(0, 0, 0, 0.3)",
                                                                    padding: "1px 4px",
                                                                    borderRadius: 3,
                                                                    fontSize: "0.9em",
                                                                    fontFamily: "monospace"
                                                                }}>{children}</code>
                                                            ) : (
                                                                <code style={{
                                                                    display: "block",
                                                                    background: isLightMode ? "rgba(0, 0, 0, 0.05)" : "rgba(0, 0, 0, 0.3)",
                                                                    padding: "6px 8px",
                                                                    borderRadius: 4,
                                                                    fontSize: "0.9em",
                                                                    fontFamily: "monospace",
                                                                    overflow: "auto",
                                                                    margin: "4px 0"
                                                                }}>{children}</code>
                                                            )
                                                        },
                                                    }}
                                                >
                                                    {event.message}
                                                </ReactMarkdown>
                                            </div>
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
