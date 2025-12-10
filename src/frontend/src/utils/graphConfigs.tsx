/**
 * Graph Configuration
 * 
 * Defines the node and edge configurations for the orchestrator visualization.
 */

import type { Node, Edge } from "@xyflow/react"
import { Brain, MapPin, CircleDollarSign, Package, Zap } from "lucide-react"
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
    backgroundColor: "var(--group-background)",
    border: "1px dashed var(--group-border)",
    borderRadius: "16px",
}

export const ORCHESTRATOR_CONFIG: GraphConfig = {
    title: "Logistics Orchestrator Network",
    nodes: [
        // Group container
        {
            id: NODE_IDS.ORCHESTRATOR_GROUP,
            type: "group",
            data: { label: "Logistics Orchestrator" },
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
                label1: "Supervisor",
                label2: "Orchestrator Agent",
                handles: "source",
                status: "idle",
                description: "Routes requests to specialized agents",
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
            position: { x: 120, y: 180 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...transportStyle,
        },
        // Serviceability Agent
        {
            id: NODE_IDS.SERVICEABILITY,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: MapPin,
                label1: "Serviceability",
                label2: "Route Validation",
                handles: "target",
                status: "idle",
                description: "Validates shipping routes",
            },
            position: { x: 60, y: 300 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
        // Rate Agent
        {
            id: NODE_IDS.RATE_AGENT,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: CircleDollarSign,
                label1: "Rate Agent",
                label2: "Quote Aggregation",
                handles: "target",
                status: "idle",
                description: "Aggregates carrier quotes",
            },
            position: { x: 280, y: 300 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
        // Carrier Agent
        {
            id: NODE_IDS.CARRIER,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: Package,
                label1: "Carrier Agent",
                label2: "Booking Execution",
                handles: "target",
                status: "idle",
                description: "Executes shipment bookings",
            },
            position: { x: 500, y: 300 },
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
        // SLIM to Serviceability
        {
            id: EDGE_IDS.SLIM_TO_SERVICEABILITY,
            source: NODE_IDS.SLIM_TRANSPORT,
            target: NODE_IDS.SERVICEABILITY,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom-left",
            data: { label: "" },
            animated: false,
        },
        // SLIM to Rate Agent
        {
            id: EDGE_IDS.SLIM_TO_RATE,
            source: NODE_IDS.SLIM_TRANSPORT,
            target: NODE_IDS.RATE_AGENT,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom-center",
            data: { label: "" },
            animated: false,
        },
        // SLIM to Carrier
        {
            id: EDGE_IDS.SLIM_TO_CARRIER,
            source: NODE_IDS.SLIM_TRANSPORT,
            target: NODE_IDS.CARRIER,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom-right",
            data: { label: "" },
            animated: false,
        },
    ],
    animationSequence: [
        { ids: [NODE_IDS.SUPERVISOR] },
        { ids: [EDGE_IDS.SUPERVISOR_TO_SLIM] },
        { ids: [NODE_IDS.SLIM_TRANSPORT] },
        { ids: [EDGE_IDS.SLIM_TO_SERVICEABILITY, EDGE_IDS.SLIM_TO_RATE, EDGE_IDS.SLIM_TO_CARRIER] },
        { ids: [NODE_IDS.SERVICEABILITY, NODE_IDS.RATE_AGENT, NODE_IDS.CARRIER] },
    ],
}

export const getGraphConfig = (): GraphConfig => {
    return ORCHESTRATOR_CONFIG
}
