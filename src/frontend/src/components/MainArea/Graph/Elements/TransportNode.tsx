/**
 * Transport Node Component
 * 
 * SLIM transport node with theme-aware styling.
 */

import React from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import { Zap } from "lucide-react"
import { useTheme } from "@/contexts/ThemeContext"

interface TransportNodeData {
    label: string
    active?: boolean
}

const TransportNode: React.FC<NodeProps> = ({ data }) => {
    const nodeData = data as unknown as TransportNodeData
    const isActive = nodeData.active
    const { isLightMode } = useTheme()

    // Theme-aware colors
    const getBackground = () => {
        if (isLightMode) {
            // Light theme: lighter green gradient
            return isActive
                ? "linear-gradient(90deg, #50D387 0%, #80e0a8 50%, #50D387 100%)"
                : "linear-gradient(90deg, #50D387 0%, #80e0a8 100%)"
        } else {
            // Dark theme: darker green gradient
            return isActive
                ? "linear-gradient(90deg, #003323 0%, #50D387 50%, #003323 100%)"
                : "linear-gradient(90deg, #003323 0%, #004d2e 100%)"
        }
    }

    const getBorderColor = () => {
        return isLightMode
            ? "rgba(80, 211, 135, 0.4)"
            : "rgba(80, 211, 135, 0.3)"
    }

    const getBoxShadow = () => {
        if (isActive) {
            return isLightMode
                ? "0 0 25px rgba(80, 211, 135, 0.4), 0 4px 12px rgba(0, 0, 0, 0.1)"
                : "0 0 30px rgba(80, 211, 135, 0.5), 0 4px 12px rgba(0, 0, 0, 0.2)"
        }
        return isLightMode
            ? "0 2px 8px rgba(0, 0, 0, 0.08)"
            : "0 2px 8px rgba(0, 0, 0, 0.15)"
    }

    const getTextColor = () => {
        return isLightMode ? "#ffffff" : "#ffffff"
    }

    const getSubtextColor = () => {
        return isLightMode ? "rgba(255, 255, 255, 0.85)" : "rgba(255, 255, 255, 0.7)"
    }

    const getIconBackground = () => {
        return isLightMode
            ? "rgba(255, 255, 255, 0.25)"
            : "rgba(255, 255, 255, 0.15)"
    }

    const nodeStyles: React.CSSProperties = {
        width: 480,
        height: 56,
        padding: "0 24px",
        borderRadius: 16,
        display: "flex",
        alignItems: "center",
        gap: 16,
        background: getBackground(),
        backgroundSize: isActive ? "200% 100%" : "100% 100%",
        border: `1px solid ${getBorderColor()}`,
        boxShadow: getBoxShadow(),
        animation: isActive ? "shimmer 2s linear infinite" : "none",
        position: "relative",
        transition: "all 0.3s ease",
    }

    const iconBoxStyles: React.CSSProperties = {
        width: 36,
        height: 36,
        borderRadius: 10,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: getIconBackground(),
        backdropFilter: "blur(8px)",
    }

    const handleStyles: React.CSSProperties = {
        width: 12,
        height: 12,
        border: `2px solid ${isLightMode ? "rgba(255, 255, 255, 0.6)" : "rgba(255, 255, 255, 0.5)"}`,
        background: "#50D387",
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
                <span style={{ 
                    fontSize: 14, 
                    fontWeight: 600, 
                    color: getTextColor() 
                }}>
                    {nodeData.label}
                </span>
                <span style={{ 
                    fontSize: 11, 
                    color: getSubtextColor() 
                }}>
                    A2A Message Transport
                </span>
            </div>

            {/* Output handles */}
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom-center"
                style={{ ...handleStyles, bottom: -6, left: "50%" }}
            />
        </div>
    )
}

export default TransportNode
