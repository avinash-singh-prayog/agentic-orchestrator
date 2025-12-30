/**
 * Graph Configuration
 * 
 * Defines the node and edge configurations for the orchestrator visualization.
 */

import type { Node, Edge } from "@xyflow/react"
import { Brain, Package, Zap, ShoppingCart, User, Cloud, Search } from "lucide-react"
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

// Small node style for MCP servers
const smallNodeStyle = {
    width: 140,
    height: 80,
}

// Transport node style
const transportStyle = {
    width: 600,
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
            style: { ...groupStyle, width: 950, height: 550 },
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
            position: { x: 180, y: 40 },
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
            position: { x: 550, y: 40 },
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
            position: { x: 100, y: 180 },
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
            position: { x: 60, y: 320 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
        // Booking Agent (Bottom Center-Left)
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
            position: { x: 280, y: 320 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
        // Personal Assistant Agent (Bottom Center-Right)
        {
            id: NODE_IDS.PERSONAL_ASSISTANT,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: User,
                label1: "Personal Assistant",
                label2: "MCP Integration",
                handles: "all",
                status: "idle",
                description: "Weather, Search & productivity",
            },
            position: { x: 500, y: 320 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...nodeStyle,
        },
        // Weather MCP (Bottom Right - under PA)
        {
            id: NODE_IDS.WEATHER_MCP,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: Cloud,
                label1: "Weather MCP",
                label2: "FastMCP Server",
                handles: "target",
                status: "idle",
                description: "Weather data tools",
            },
            position: { x: 460, y: 460 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...smallNodeStyle,
        },
        // WebSearch MCP (Bottom Far Right - under PA)
        {
            id: NODE_IDS.WEBSEARCH_MCP,
            type: NODE_TYPES.CUSTOM,
            data: {
                icon: Search,
                label1: "WebSearch MCP",
                label2: "FastMCP Server",
                handles: "target",
                status: "idle",
                description: "Web search & extraction",
            },
            position: { x: 620, y: 460 },
            parentId: NODE_IDS.ORCHESTRATOR_GROUP,
            ...smallNodeStyle,
        },
    ],
    edges: [
        // Supervisor to SLIM Transport (Vertical)
        {
            id: EDGE_IDS.SUPERVISOR_TO_SLIM,
            source: NODE_IDS.SUPERVISOR,
            target: NODE_IDS.SLIM_TRANSPORT,
            sourceHandle: "bottom",
            targetHandle: "top",
            type: EDGE_TYPES.CUSTOM,
            data: { label: "A2A" },
            animated: false,
        },
        // Supervisor to Directory (Horizontal)
        {
            id: "supervisor-to-directory",
            source: NODE_IDS.SUPERVISOR,
            target: "directory-service",
            sourceHandle: "right",
            targetHandle: "left",
            type: EDGE_TYPES.CUSTOM,
            data: { label: "Lookup" },
            style: { strokeDasharray: "5, 5" },
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
        // SLIM to Personal Assistant
        {
            id: EDGE_IDS.SLIM_TO_PERSONAL_ASSISTANT,
            source: NODE_IDS.SLIM_TRANSPORT,
            target: NODE_IDS.PERSONAL_ASSISTANT,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom-center",
            targetHandle: "top",
            data: { label: "" },
            animated: false,
        },
        // Personal Assistant to Weather MCP
        {
            id: EDGE_IDS.PA_TO_WEATHER_MCP,
            source: NODE_IDS.PERSONAL_ASSISTANT,
            target: NODE_IDS.WEATHER_MCP,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom",
            targetHandle: "top",
            data: { label: "" },
            style: { strokeDasharray: "3, 3" },
            animated: false,
        },
        // Personal Assistant to WebSearch MCP
        {
            id: EDGE_IDS.PA_TO_WEBSEARCH_MCP,
            source: NODE_IDS.PERSONAL_ASSISTANT,
            target: NODE_IDS.WEBSEARCH_MCP,
            type: EDGE_TYPES.CUSTOM,
            sourceHandle: "bottom",
            targetHandle: "top",
            data: { label: "" },
            style: { strokeDasharray: "3, 3" },
            animated: false,
        },
    ],
    animationSequence: [
        { ids: [NODE_IDS.SUPERVISOR] },
        { ids: [EDGE_IDS.SUPERVISOR_TO_SLIM] },
        { ids: [NODE_IDS.SLIM_TRANSPORT] },
        { ids: [EDGE_IDS.SLIM_TO_SERVICEABILITY_AGENT, EDGE_IDS.SLIM_TO_BOOKING_AGENT, EDGE_IDS.SLIM_TO_PERSONAL_ASSISTANT] },
        { ids: [NODE_IDS.SERVICEABILITY_AGENT, NODE_IDS.BOOKING_AGENT, NODE_IDS.PERSONAL_ASSISTANT] },
        { ids: [EDGE_IDS.PA_TO_WEATHER_MCP, EDGE_IDS.PA_TO_WEBSEARCH_MCP] },
        { ids: [NODE_IDS.WEATHER_MCP, NODE_IDS.WEBSEARCH_MCP] },
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
