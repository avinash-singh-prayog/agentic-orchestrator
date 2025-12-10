/**
 * Main Area Component
 * 
 * Contains the ReactFlow graph visualization.
 */

import React, { useMemo, useCallback } from "react"
import {
    ReactFlow,
    ReactFlowProvider,
    Controls,
    Background,
    BackgroundVariant,
    useNodesState,
    useEdgesState,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import { CustomNode, TransportNode, CustomEdge } from "./Graph/Elements"
import { getGraphConfig } from "@/utils/graphConfigs"

interface MainAreaProps {
    isProcessing?: boolean
    activeNodeId?: string | null
}

const MainAreaContent: React.FC<MainAreaProps> = ({
    isProcessing = false,
    activeNodeId = null,
}) => {
    const config = useMemo(() => getGraphConfig(), [])

    // Apply active state to nodes
    const initialNodes = useMemo(() => {
        return config.nodes.map((node) => ({
            ...node,
            data: {
                ...node.data,
                status: node.id === activeNodeId ? "processing" : "idle",
            },
        }))
    }, [config.nodes, activeNodeId])

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(config.edges)

    // Custom node types
    const nodeTypes = useMemo(
        () => ({
            customNode: CustomNode,
            transportNode: TransportNode,
        }),
        []
    )

    // Custom edge types
    const edgeTypes = useMemo(
        () => ({
            custom: CustomEdge,
        }),
        []
    )

    // Update node status when activeNodeId changes
    React.useEffect(() => {
        setNodes((nds) =>
            nds.map((node) => ({
                ...node,
                data: {
                    ...node.data,
                    status: node.id === activeNodeId ? "processing" : "idle",
                },
            }))
        )
    }, [activeNodeId, setNodes])

    // Update edge animation when processing
    React.useEffect(() => {
        setEdges((eds) =>
            eds.map((edge) => ({
                ...edge,
                data: {
                    ...edge.data,
                    animated: isProcessing,
                },
            }))
        )
    }, [isProcessing, setEdges])

    const onNodeClick = useCallback((_event: React.MouseEvent, node: { id: string }) => {
        console.log("Node clicked:", node.id)
    }, [])

    return (
        <div className="h-full w-full bg-app-background">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                fitView
                fitViewOptions={{
                    padding: 0.2,
                    maxZoom: 1,
                }}
                minZoom={0.3}
                maxZoom={1.5}
                attributionPosition="bottom-left"
                proOptions={{ hideAttribution: true }}
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={20}
                    size={1}
                    color="var(--border-color)"
                />
                <Controls
                    showInteractive={false}
                    className="!rounded-lg !border !border-border-color !bg-node-background"
                />
            </ReactFlow>
        </div>
    )
}

const MainArea: React.FC<MainAreaProps> = (props) => {
    return (
        <ReactFlowProvider>
            <MainAreaContent {...props} />
        </ReactFlowProvider>
    )
}

export default MainArea
