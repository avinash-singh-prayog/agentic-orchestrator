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
                        ? "#50D387"
                        : selected
                            ? "#50D387"
                            : "var(--border-subtle)",
                    strokeWidth: isAnimated ? 3 : 2,
                    filter: isAnimated ? "drop-shadow(0 0 8px rgba(80, 211, 135, 0.6))" : "none",
                    transition: "all 0.3s ease",
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
                            opacity: 0.65,
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
                    <circle r="4" fill="#50D387" filter="url(#glowFilter)">
                        <animateMotion
                            dur={`${pathLength / 60}s`}
                            repeatCount="indefinite"
                            path={edgePath}
                        />
                    </circle>

                    {/* Gradient and filter definitions */}
                    <defs>
                        <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#50D387" />
                            <stop offset="50%" stopColor="#80e0a8" />
                            <stop offset="100%" stopColor="#50D387" />
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
                        fill: isAnimated ? "#50D387" : "var(--text-tertiary)",
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
