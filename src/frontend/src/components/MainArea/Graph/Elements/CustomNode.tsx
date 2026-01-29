/**
 * Custom Node Component
 * 
 * Premium styled agent node with inline styles for reliability.
 */

import React from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import type { LucideIcon } from "lucide-react"

interface CustomNodeData {
    icon: LucideIcon
    label1: string
    label2: string
    handles: "source" | "target" | "all"
    status?: "idle" | "processing" | "completed" | "error"
}

const CustomNode: React.FC<NodeProps> = ({ data }) => {
    const nodeData = data as unknown as CustomNodeData
    const Icon = nodeData.icon
    const status = nodeData.status || "idle"
    const isActive = status === "processing"

    const nodeStyles: React.CSSProperties = {
        width: 190,
        height: 105,
        padding: "16px",
        borderRadius: "16px",
        display: "flex",
        flexDirection: "column",
        background: "var(--bg-panel)",
        border: status === "processing"
            ? "2px solid #50D387"
            : "1px solid var(--border-subtle)",
        boxShadow: status === "processing"
            ? "0 0 20px rgba(80, 211, 135, 0.4), 0 4px 12px rgba(0, 0, 0, 0.15)"
            : "0 2px 8px rgba(0, 0, 0, 0.1)",
        transition: "all 0.3s ease",
        position: "relative",
    }

    const iconBgStyles: React.CSSProperties = {
        width: 36,
        height: 36,
        borderRadius: 10,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        marginBottom: 10,
        background: status === "processing"
            ? "linear-gradient(135deg, #50D387, #80e0a8)"
            : status === "completed"
                ? "linear-gradient(135deg, #50D387, #80e0a8)"
                : "linear-gradient(135deg, #003323, #004d2e)",
        boxShadow: status === "processing"
            ? "0 4px 12px rgba(80, 211, 135, 0.4)"
            : "0 2px 6px rgba(0, 0, 0, 0.2)",
    }

    const statusDotStyles: React.CSSProperties = {
        position: "absolute",
        top: 12,
        right: 12,
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: status === "processing" ? "#50D387"
            : status === "completed" ? "#50D387"
                : status === "error" ? "#f87171"
                    : "var(--text-tertiary)",
        animation: status === "processing" ? "pulse 2s infinite" : "none",
    }

    const handleStyles: React.CSSProperties = {
        width: 12,
        height: 12,
        border: "2px solid #50D387",
        background: "var(--bg-panel)",
    }

    return (
        <div style={nodeStyles} className={isActive ? "node-active" : ""}>
            {/* Status dot */}
            <div style={statusDotStyles} />

            {/* Icon */}
            <div style={iconBgStyles}>
                <Icon style={{ width: 18, height: 18, color: "white" }} />
            </div>

            {/* Labels */}
            <span style={{
                fontSize: 14,
                fontWeight: 600,
                color: "var(--text-primary)",
                lineHeight: 1.2,
                marginBottom: 2,
            }}>
                {nodeData.label1}
            </span>
            <span style={{
                fontSize: 11,
                color: "var(--text-secondary)",
                fontWeight: 500,
            }}>
                {nodeData.label2}
            </span>

            {/* Handles */}
            {(nodeData.handles === "all" || nodeData.handles === "target") && (
                <Handle
                    type="target"
                    position={Position.Top}
                    style={{ ...handleStyles, top: -6 }}
                />
            )}
            {(nodeData.handles === "all" || nodeData.handles === "source") && (
                <Handle
                    type="source"
                    position={Position.Bottom}
                    style={{ ...handleStyles, bottom: -6 }}
                />
            )}
        </div>
    )
}

export default CustomNode
