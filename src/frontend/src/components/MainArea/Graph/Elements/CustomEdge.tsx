/**
 * Custom Edge Component
 * 
 * Animated edge for connections between nodes.
 */

import React from "react"
import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/react"

interface CustomEdgeData {
    label?: string
    animated?: boolean
}

const CustomEdge: React.FC<EdgeProps> = ({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    data,
    selected,
}) => {
    const edgeData = data as CustomEdgeData | undefined

    const [edgePath] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    })

    const isAnimated = edgeData?.animated

    return (
        <>
            <BaseEdge
                id={id}
                path={edgePath}
                style={{
                    stroke: selected ? "var(--accent-primary)" : "var(--border-color)",
                    strokeWidth: selected ? 2.5 : 2,
                    opacity: 0.8,
                }}
            />
            {isAnimated && (
                <path
                    d={edgePath}
                    fill="none"
                    stroke="var(--accent-primary)"
                    strokeWidth={2}
                    strokeDasharray="8 4"
                    className="animate-edge-flow"
                    style={{
                        animation: "edgeFlow 1s linear infinite",
                    }}
                />
            )}
            {edgeData?.label && (
                <text
                    x={(sourceX + targetX) / 2}
                    y={(sourceY + targetY) / 2 - 10}
                    textAnchor="middle"
                    className="fill-node-text-secondary text-xs"
                >
                    {edgeData.label}
                </text>
            )}
        </>
    )
}

export default CustomEdge
