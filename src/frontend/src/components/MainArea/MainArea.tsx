/**
 * Main Area Component
 * 
 * ReactFlow graph with targeted agent flow visualization.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react"
import {
    ReactFlow,
    Background,
    Controls,
    useNodesState,
    useEdgesState,
    BackgroundVariant,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import { CustomNode, TransportNode, CustomEdge } from "./Graph/Elements"
import { getInitialNodes, getInitialEdges } from "@/utils/graphConfigs"
import { useStreamingEvents, useStreamingStatus } from "@/stores/orchestratorStreamingStore"

const nodeTypes = {
    customNode: CustomNode,
    transportNode: TransportNode,
}

const edgeTypes = {
    custom: CustomEdge,
}

// Map sender names from backend to specific animation paths
// Only animate the exact path for the agent being called
const getAnimationPath = (sender: string): { nodes: string[], edges: string[] } => {
    const senderLower = sender.toLowerCase()

    // Base path always includes supervisor and transport
    const basePath = {
        nodes: ["supervisor", "slim-transport"],
        edges: ["supervisor-to-slim"],
    }

    if (senderLower.includes("serviceability") || senderLower === "serviceability_agent") {
        return {
            nodes: [...basePath.nodes, "serviceability"],
            edges: [...basePath.edges, "slim-to-serviceability"],
        }
    }

    if (senderLower.includes("rate") || senderLower === "rate_agent") {
        return {
            nodes: [...basePath.nodes, "rate-agent"],
            edges: [...basePath.edges, "slim-to-rate"],
        }
    }

    if (senderLower.includes("carrier") || senderLower === "carrier_agent") {
        return {
            nodes: [...basePath.nodes, "carrier"],
            edges: [...basePath.edges, "slim-to-carrier"],
        }
    }

    // Default: only supervisor
    if (senderLower.includes("supervisor")) {
        return {
            nodes: ["supervisor"],
            edges: [],
        }
    }

    return { nodes: [], edges: [] }
}

interface MainAreaProps {
    isProcessing?: boolean
    activeAgent?: string | null
}

const MainArea: React.FC<MainAreaProps> = ({ isProcessing, activeAgent: syncActiveAgent }) => {
    const initialNodes = useMemo(() => getInitialNodes(), [])
    const initialEdges = useMemo(() => getInitialEdges(), [])

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

    // Track which specific nodes and edges should animate
    const [activeNodes, setActiveNodes] = useState<Set<string>>(new Set())
    const [activeEdges, setActiveEdges] = useState<Set<string>>(new Set())

    // Get streaming events to determine which agent is active
    const events = useStreamingEvents()
    const streamingStatus = useStreamingStatus()

    // Determine active agent name - from streaming events or sync prop
    const activeAgentName = useMemo(() => {
        if (streamingStatus === "streaming" && events.length > 0) {
            return events[events.length - 1].sender
        }
        return syncActiveAgent || null
    }, [events, streamingStatus, syncActiveAgent])

    // Update animation paths based on active agent
    useEffect(() => {
        if (!activeAgentName && !isProcessing) {
            // Reset when neither streaming nor processing
            setActiveNodes(new Set())
            setActiveEdges(new Set())
            return
        }

        if (activeAgentName) {
            const path = getAnimationPath(activeAgentName)
            setActiveNodes(new Set(path.nodes))
            setActiveEdges(new Set(path.edges))
        } else if (isProcessing) {
            // Sync mode starting - just show supervisor
            setActiveNodes(new Set(["supervisor"]))
            setActiveEdges(new Set())
        }
    }, [activeAgentName, isProcessing])

    // Update node visual states
    useEffect(() => {
        setNodes((nds) =>
            nds.map((node) => {
                const isActive = activeNodes.has(node.id)
                const isTransport = node.type === "transportNode"

                return {
                    ...node,
                    data: {
                        ...node.data,
                        status: isActive ? "processing" : "idle",
                        active: isTransport && activeNodes.has("slim-transport"),
                    },
                }
            })
        )
    }, [activeNodes, setNodes])

    // Update edge visual states
    useEffect(() => {
        setEdges((eds) =>
            eds.map((edge) => ({
                ...edge,
                data: {
                    ...edge.data,
                    animated: activeEdges.has(edge.id),
                },
            }))
        )
    }, [activeEdges, setEdges])

    const onNodeClick = useCallback((_event: React.MouseEvent, node: { id: string }) => {
        console.log("Node clicked:", node.id)
    }, [])

    const containerStyles: React.CSSProperties = {
        position: "relative",
        height: "100%",
        width: "100%",
        background: "linear-gradient(135deg, #14161e 0%, #1a1d28 50%, #14161e 100%)",
    }

    return (
        <div style={containerStyles}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                fitView
                fitViewOptions={{ padding: 0.25 }}
                minZoom={0.4}
                maxZoom={1.5}
                defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
                proOptions={{ hideAttribution: true }}
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={24}
                    size={1}
                    color="rgba(139, 156, 184, 0.1)"
                />
                <Controls showInteractive={false} />
            </ReactFlow>

            {/* Processing indicator with active agent */}
            {(isProcessing || streamingStatus === "streaming") && activeAgentName && (
                <div style={{
                    position: "absolute",
                    top: 16,
                    left: 16,
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "10px 16px",
                    borderRadius: 12,
                    background: "rgba(20, 22, 30, 0.95)",
                    border: "1px solid rgba(79, 143, 255, 0.4)",
                    backdropFilter: "blur(12px)",
                    boxShadow: "0 4px 20px rgba(79, 143, 255, 0.2)",
                }}>
                    <div style={{
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        background: "linear-gradient(135deg, #4f8fff, #9d7cf6)",
                        animation: "pulse 1.5s infinite",
                    }} />
                    <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontSize: 11, color: "#a8b5cf", textTransform: "uppercase", letterSpacing: 1 }}>
                            Active Agent
                        </span>
                        <span style={{ fontSize: 14, fontWeight: 600, color: "#6ba6ff" }}>
                            {activeAgentName}
                        </span>
                    </div>
                </div>
            )}
        </div>
    )
}

export default MainArea
