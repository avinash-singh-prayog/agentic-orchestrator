/**
 * Graph Configuration
 * 
 * Defines the node and edge configurations for the orchestrator visualization.
 */

import type { Node, Edge } from "@xyflow/react"
import { Brain, Zap, FileSearch } from "lucide-react"
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

// Group container style (theme-aware using CSS variables)
const groupStyle = {
    width: 740,
    height: 400,
    backgroundColor: "var(--bg-panel)",
    border: "1px dashed var(--border-subtle)",
    borderRadius: "16px",
    opacity: 0.8,
}

export const ORCHESTRATOR_CONFIG: GraphConfig = {
    title: "PineLabs AI Network",
    nodes: [
        // Group container
        {
            id: NODE_IDS.ORCHESTRATOR_GROUP,
            type: "group",
            data: { label: "PineLabs AI" },
            position: { x: 50, y: 50 },
            style: groupStyle,
            draggable: false,
        },
        // Supervisor Agent
        {
            id: NODE_IDS.SUPERVISOR,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: Brain,
                label1: "Supervisor Agent",
                label2: "Orchestrator Agent",
                handles: "source",
                status: "idle",
                description: "Routes requests to Transaction RCA Agent",
            },
            position: { x: 280, y: 40 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
        // SLIM Transport
        {
            id: NODE_IDS.SLIM_TRANSPORT,
            type: NODE_TYPES.TRANSPORT,
            data: {
                label: "SLIM Transport",
                icon: Zap,
                description: "A2A Message Bus",
            },
            position: { x: 220, y: 180 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...transportStyle,
        },
        // Transaction RCA Agent
        {
            id: NODE_IDS.TRANSACTION_RCA_AGENT,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: FileSearch,
                label1: "Transaction RCA Agent",
                label2: "Root Cause Analysis",
                handles: "target",
                status: "idle",
                description: "Analyzes transaction failures",
            },
            position: { x: 280, y: 300 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
    ],
    edges: [
        // Supervisor to SLIM Transport
        {
            id: EDGE_IDS.SUPERVISOR_TO_SLIM,
            source: NODE_IDS.SUPERVISOR,
            target: NODE_IDS.SLIM_TRANSPORT,
            type: EDGE_TYPES.CUSTOM,
            data: { label: "A2A" },
            animated: false,
        },
        // SLIM to Transaction RCA Agent
        {
            id: EDGE_IDS.SLIM_TO_TRANSACTION_RCA_AGENT,
            source: NODE_IDS.SLIM_TRANSPORT,
            target: NODE_IDS.TRANSACTION_RCA_AGENT,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom-center",
            data: { label: "" },
            animated: false,
        },
    ],
    animationSequence: [
        { ids: [NODE_IDS.SUPERVISOR] },
        { ids: [EDGE_IDS.SUPERVISOR_TO_SLIM] },
        { ids: [NODE_IDS.SLIM_TRANSPORT] },
        { ids: [EDGE_IDS.SLIM_TO_TRANSACTION_RCA_AGENT] },
        { ids: [NODE_IDS.TRANSACTION_RCA_AGENT] },
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

