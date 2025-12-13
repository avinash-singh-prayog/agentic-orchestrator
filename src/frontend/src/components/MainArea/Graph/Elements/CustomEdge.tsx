/**
 * Custom Edge Component
 * 
 * Animated edge with flowing gradient particles.
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
    const isAnimated = edgeData?.animated

    const [edgePath] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    })

    // Calculate path length for animation
    const pathLength = Math.sqrt(
        Math.pow(targetX - sourceX, 2) + Math.pow(targetY - sourceY, 2)
    )

    return (
        <>
            {/* Base edge - subtle glow when animated */}
            <BaseEdge
                id={id}
                path={edgePath}
                style={{
                    stroke: isAnimated
                        ? "rgba(59, 130, 246, 0.4)"
                        : selected
                            ? "#3b82f6"
                            : "rgba(148, 163, 184, 0.25)",
                    strokeWidth: isAnimated ? 3 : 2,
                    filter: isAnimated ? "drop-shadow(0 0 6px rgba(59, 130, 246, 0.5))" : "none",
                }}
            />

            {/* Animated flowing particles when active */}
            {isAnimated && (
                <>
                    {/* Glow underneath */}
                    <path
                        d={edgePath}
                        fill="none"
                        stroke="url(#flowGradient)"
                        strokeWidth={4}
                        strokeLinecap="round"
                        style={{
                            filter: "blur(4px)",
                            opacity: 0.6,
                        }}
                    />

                    {/* Flowing dashed line */}
                    <path
                        d={edgePath}
                        fill="none"
                        stroke="url(#flowGradient)"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeDasharray="12 8"
                        style={{
                            animation: `flowDash ${pathLength / 80}s linear infinite`,
                        }}
                    />

                    {/* Moving particle dot */}
                    <circle r="4" fill="#60a5fa" filter="url(#glowFilter)">
                        <animateMotion
                            dur={`${pathLength / 60}s`}
                            repeatCount="indefinite"
                            path={edgePath}
                        />
                    </circle>

                    {/* Gradient and filter definitions */}
                    <defs>
                        <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#3b82f6" />
                            <stop offset="50%" stopColor="#8b5cf6" />
                            <stop offset="100%" stopColor="#3b82f6" />
                        </linearGradient>
                        <filter id="glowFilter" x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                            <feMerge>
                                <feMergeNode in="coloredBlur" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>
                    </defs>
                </>
            )}

            {/* Label */}
            {edgeData?.label && (
                <text
                    x={(sourceX + targetX) / 2}
                    y={(sourceY + targetY) / 2 - 10}
                    textAnchor="middle"
                    style={{
                        fontSize: 10,
                        fill: isAnimated ? "#60a5fa" : "#64748b",
                        fontWeight: 500,
                    }}
                >
                    {edgeData.label}
                </text>
            )}
        </>
    )
}

export default CustomEdge
