/**
 * Custom Node Component
 * 
 * Renders an agent node with icon, labels, and status indicators.
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
    description?: string
}

const statusColors = {
    idle: "bg-gray-500",
    processing: "bg-accent-primary animate-pulse",
    completed: "bg-success",
    error: "bg-error",
}

const CustomNode: React.FC<NodeProps> = ({ data }) => {
    const nodeData = data as unknown as CustomNodeData
    const Icon = nodeData.icon
    const status = nodeData.status || "idle"

    const isActive = status === "processing" || status === "completed"
    const activeClasses = isActive
        ? "bg-node-background-active ring-2 ring-accent-primary shadow-lg shadow-accent-primary/20"
        : "bg-node-background hover:bg-node-background-hover"

    return (
        <div
            className={`
        relative flex flex-col rounded-xl p-4 transition-all duration-300 ease-in-out
        border border-border-color
        ${activeClasses}
      `}
            style={{ width: 180, height: 95 }}
        >
            {/* Status indicator */}
            <div
                className={`absolute top-3 right-3 h-2 w-2 rounded-full ${statusColors[status]}`}
            />

            {/* Icon */}
            <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-accent-primary/20">
                <Icon className="h-4 w-4 text-accent-primary" />
            </div>

            {/* Labels */}
            <span className="text-sm font-semibold text-node-text-primary">
                {nodeData.label1}
            </span>
            <span className="text-xs text-node-text-secondary">{nodeData.label2}</span>

            {/* Handles */}
            {(nodeData.handles === "all" || nodeData.handles === "target") && (
                <Handle
                    type="target"
                    position={Position.Top}
                    className="!h-3 !w-3 !border-2 !border-accent-primary !bg-node-background"
                />
            )}
            {(nodeData.handles === "all" || nodeData.handles === "source") && (
                <Handle
                    type="source"
                    position={Position.Bottom}
                    className="!h-3 !w-3 !border-2 !border-accent-primary !bg-node-background"
                />
            )}
        </div>
    )
}

export default CustomNode
