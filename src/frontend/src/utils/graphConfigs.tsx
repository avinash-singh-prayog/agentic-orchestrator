/**
 * Graph Configuration
 * 
 * Defines the node and edge configurations for the orchestrator visualization.
 */

import type { Node, Edge } from "@xyflow/react"
import { Brain, Package, Zap, ShoppingCart } from "lucide-react"
import { NODE_IDS, EDGE_IDS, NODE_TYPES, EDGE_TYPES } from "./const"

export interface GraphConfig {
    title: string
    nodes: Node[]
    edges: Edge[]
    animationSequence: { ids: string[] }[]
}

// Default node style
const nodeStyle = {
    width: 180,
    height: 95,
}

// Transport node style
const transportStyle = {
    width: 500,
    height: 52,
}

// Group container style
const groupStyle = {
    width: 740,
    height: 500,
    backgroundColor: "rgba(26, 29, 40, 0.4)",
    border: "1px dashed rgba(139, 156, 184, 0.2)",
    borderRadius: "16px",
}

export const ORCHESTRATOR_CONFIG: GraphConfig = {
    title: "Agentic Orchestrator Network",
    nodes: [
        // Group container
        {
            id: NODE_IDS.ORCHESTRATOR_GROUP,
            type: "group",
            data: { label: "Agentic Orchestrator" },
            position: { x: 50, y: 50 },
            style: { ...groupStyle, width: 850 }, // Widen container
            draggable: false,
        },
        // Supervisor Agent (Top Left)
        {
            id: NODE_IDS.SUPERVISOR,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: Brain,
                label1: "Supervisor Agent",
                label2: "Orchestrator Agent",
                handles: "source",
                status: "idle",
                description: "Routes requests to specialized agents",
            },
            position: { x: 180, y: 40 }, // Shifted Left
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
        // Directory Service (Top Right)
        {
            id: "directory-service",
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: Package,
                label1: "Directory Service",
                label2: "Agent Registry",
                handles: "target",
                status: "idle",
                description: "Capability Lookup",
            },
            position: { x: 550, y: 40 }, // Far Right
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
            style: { ...nodeStyle, width: 170 },
        },
        // SLIM Transport (Centered below Supervisor)
        {
            id: NODE_IDS.SLIM_TRANSPORT,
            type: NODE_TYPES.TRANSPORT,
            data: {
                label: "SLIM Transport",
                icon: Zap,
                description: "A2A Message Bus",
            },
            position: { x: 120, y: 180 }, // Centered under group
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...transportStyle,
        },
        // Serviceability Agent (Bottom Left)
        {
            id: NODE_IDS.SERVICEABILITY_AGENT,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: Package,
                label1: "Serviceability Agent",
                label2: "Logistics Fulfillment",
                handles: "target",
                status: "idle",
                description: "Checks rates and serviceability",
            },
            position: { x: 120, y: 320 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
        // Booking Agent (Bottom Right)
        {
            id: NODE_IDS.BOOKING_AGENT,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: ShoppingCart,
                label1: "Booking Agent",
                label2: "Order Management",
                handles: "target",
                status: "idle",
                description: "Creates and manages orders",
            },
            position: { x: 440, y: 320 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
    ],
    edges: [
        // Supervisor to SLIM Transport (Vertical)
        {
            id: EDGE_IDS.SUPERVISOR_TO_SLIM,
            source: NODE_IDS.SUPERVISOR,
            target: NODE_IDS.SLIM_TRANSPORT,
            sourceHandle: "bottom",
            targetHandle: "top", // implicit for TransportNode usually
            type: EDGE_TYPES.CUSTOM,
            data: { label: "A2A" },
            animated: false,
        },
        // Supervisor to Directory (Horizontal)
        {
            id: "supervisor-to-directory",
            source: NODE_IDS.SUPERVISOR,
            target: "directory-service",
            sourceHandle: "right", // Use side handles
            targetHandle: "left",
            type: EDGE_TYPES.CUSTOM,
            data: { label: "Lookup" },
            style: { strokeDasharray: "5, 5" }, // Dashed line for lookup
            animated: false,
        },
        // SLIM to Serviceability Agent
        {
            id: EDGE_IDS.SLIM_TO_SERVICEABILITY_AGENT,
            source: NODE_IDS.SLIM_TRANSPORT,
            target: NODE_IDS.SERVICEABILITY_AGENT,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom-center",
            targetHandle: "top",
            data: { label: "" },
            animated: false,
        },
        // SLIM to Booking Agent
        {
            id: EDGE_IDS.SLIM_TO_BOOKING_AGENT,
            source: NODE_IDS.SLIM_TRANSPORT,
            target: NODE_IDS.BOOKING_AGENT,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom-center",
            targetHandle: "top",
            data: { label: "" },
            animated: false,
        },
    ],
    animationSequence: [
        { ids: [NODE_IDS.SUPERVISOR] },
        { ids: [EDGE_IDS.SUPERVISOR_TO_SLIM] },
        { ids: [NODE_IDS.SLIM_TRANSPORT] },
        { ids: [EDGE_IDS.SLIM_TO_SERVICEABILITY_AGENT, EDGE_IDS.SLIM_TO_BOOKING_AGENT] },
        { ids: [NODE_IDS.SERVICEABILITY_AGENT, NODE_IDS.BOOKING_AGENT] },
    ],
}

export const getGraphConfig = (): GraphConfig => {
    return ORCHESTRATOR_CONFIG
}

export const getInitialNodes = (): Node[] => {
    return ORCHESTRATOR_CONFIG.nodes
}

export const getInitialEdges = (): Edge[] => {
    return ORCHESTRATOR_CONFIG.edges
}

