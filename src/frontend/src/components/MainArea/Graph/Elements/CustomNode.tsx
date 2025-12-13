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
        background: "linear-gradient(145deg, #1a1d2e 0%, #12141f 100%)",
        border: status === "processing"
            ? "2px solid rgba(59, 130, 246, 0.6)"
            : "1px solid rgba(255, 255, 255, 0.1)",
        boxShadow: status === "processing"
            ? "0 0 30px rgba(59, 130, 246, 0.3), 0 10px 40px rgba(0, 0, 0, 0.4)"
            : "0 4px 20px rgba(0, 0, 0, 0.3)",
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
            ? "linear-gradient(135deg, #3b82f6, #8b5cf6)"
            : status === "completed"
                ? "linear-gradient(135deg, #10b981, #14b8a6)"
                : "linear-gradient(135deg, #374151, #1f2937)",
        boxShadow: status === "processing"
            ? "0 4px 15px rgba(59, 130, 246, 0.4)"
            : "0 2px 8px rgba(0, 0, 0, 0.3)",
    }

    const statusDotStyles: React.CSSProperties = {
        position: "absolute",
        top: 12,
        right: 12,
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: status === "processing" ? "#3b82f6"
            : status === "completed" ? "#10b981"
                : status === "error" ? "#ef4444"
                    : "#6b7280",
        animation: status === "processing" ? "pulse 2s infinite" : "none",
    }

    const handleStyles: React.CSSProperties = {
        width: 12,
        height: 12,
        border: "2px solid rgba(59, 130, 246, 0.5)",
        background: "#1a1d2e",
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
                color: "#f1f5f9",
                lineHeight: 1.2,
                marginBottom: 2,
            }}>
                {nodeData.label1}
            </span>
            <span style={{
                fontSize: 11,
                color: "#94a3b8",
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
