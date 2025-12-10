/**
 * Transport Node Component
 * 
 * Renders the SLIM transport / message bus node.
 */

import React from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import { Zap } from "lucide-react"

interface TransportNodeData {
    label: string
    description?: string
    active?: boolean
}

const TransportNode: React.FC<NodeProps> = ({ data }) => {
    const nodeData = data as unknown as TransportNodeData
    const isActive = nodeData.active

    return (
        <div
            className={`
        flex items-center justify-center gap-3 rounded-xl
        bg-transport-background border border-accent-primary/30
        transition-all duration-300
        ${isActive ? "shadow-lg shadow-accent-primary/30 ring-2 ring-accent-primary" : ""}
      `}
            style={{ width: 500, height: 52 }}
        >
            {/* Input handle */}
            <Handle
                type="target"
                position={Position.Top}
                id="top"
                className="!h-3 !w-3 !border-2 !border-white !bg-transport-background"
            />

            {/* Icon and label */}
            <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/10">
                    <Zap className="h-4 w-4 text-white" />
                </div>
                <span className="text-sm font-medium text-white">{nodeData.label}</span>
            </div>

            {/* Multiple output handles */}
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom-left"
                className="!h-3 !w-3 !border-2 !border-white !bg-transport-background"
                style={{ left: "20%" }}
            />
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom-center"
                className="!h-3 !w-3 !border-2 !border-white !bg-transport-background"
                style={{ left: "50%" }}
            />
            <Handle
                type="source"
                position={Position.Bottom}
                id="bottom-right"
                className="!h-3 !w-3 !border-2 !border-white !bg-transport-background"
                style={{ left: "80%" }}
            />
        </div>
    )
}

export default TransportNode
