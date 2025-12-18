/**
 * Transport Node Component
 * 
 * SLIM transport node with inline styles.
 */

import React from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import { Zap } from "lucide-react"

interface TransportNodeData {
    label: string
    active?: boolean
}

const TransportNode: React.FC<NodeProps> = ({ data }) => {
    const nodeData = data as unknown as TransportNodeData
    const isActive = nodeData.active

    const nodeStyles: React.CSSProperties = {
        width: 480,
        height: 56,
        padding: "0 24px",
        borderRadius: 16,
        display: "flex",
        alignItems: "center",
        gap: 16,
        background: "linear-gradient(90deg, #3b7cf6 0%, #8b5cf6 50%, #3b7cf6 100%)",
        backgroundSize: isActive ? "200% 100%" : "100% 100%",
        border: "1px solid rgba(255, 255, 255, 0.25)",
        boxShadow: isActive
            ? "0 0 40px rgba(139, 92, 246, 0.45), 0 10px 30px rgba(0, 0, 0, 0.25)"
            : "0 4px 20px rgba(0, 0, 0, 0.25)",
        animation: isActive ? "shimmer 2s linear infinite" : "none",
        position: "relative",
    }

    const iconBoxStyles: React.CSSProperties = {
        width: 36,
        height: 36,
        borderRadius: 10,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(255, 255, 255, 0.18)",
        backdropFilter: "blur(8px)",
    }

    const handleStyles: React.CSSProperties = {
        width: 12,
        height: 12,
        border: "2px solid rgba(255, 255, 255, 0.45)",
        background: "#8b5cf6",
    }

    return (
        <div style={nodeStyles}>
            {/* Input handle */}
            <Handle
                type="target"
                position={Position.Top}
                id="top"
                style={{ ...handleStyles, top: -6 }}
            />

            {/* Icon */}
            <div style={iconBoxStyles}>
                <Zap style={{
                    width: 18,
                    height: 18,
                    color: "white",
                    animation: isActive ? "pulse 1.5s infinite" : "none",
                }} />
            </div>

            {/* Label */}
            <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "white" }}>
                    {nodeData.label}
                </span>
                <span style={{ fontSize: 11, color: "rgba(255, 255, 255, 0.7)" }}>
                    A2A Message Transport
                </span>
            </div>

            {/* Output handles */}
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom-left"
                style={{ ...handleStyles, bottom: -6, left: "20%" }}
            />
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom-center"
                style={{ ...handleStyles, bottom: -6, left: "50%" }}
            />
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom-right"
                style={{ ...handleStyles, bottom: -6, left: "80%" }}
            />
        </div>
    )
}

export default TransportNode
