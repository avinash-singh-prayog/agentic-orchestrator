# Lungo Frontend Implementation Guide

This guide provides a detailed blueprint for replicating the Lungo Frontend in another project, specifically tailored for an **Agentic Orchestrator** application. The guide covers the project structure, dependencies, core components, state management, API integration, theming, and the interactive graph visualization system.

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Dependencies](#dependencies)
5. [Configuration Files](#configuration-files)
6. [Core Application Architecture](#core-application-architecture)
7. [Component System](#component-system)
8. [State Management](#state-management)
9. [API Integration](#api-integration)
10. [Graph Visualization System](#graph-visualization-system)
11. [Theming System](#theming-system)
12. [Types and Interfaces](#types-and-interfaces)
13. [Custom Hooks](#custom-hooks)
14. [Adaptation Guide for Agentic Orchestrator](#adaptation-guide-for-agentic-orchestrator)
15. [Step-by-Step Implementation](#step-by-step-implementation)

---

## Overview

The Lungo Frontend is a React-based visualization dashboard that displays agentic workflows using an interactive graph. It supports:

- **Multiple Communication Patterns**: Publish/Subscribe, Publish/Subscribe (Streaming), and Group Communication
- **Real-time Streaming**: SSE (Server-Sent Events) and NDJSON streaming for live updates
- **Interactive Graph**: ReactFlow-based node/edge visualization with animations
- **Theming**: Dark/Light mode support with CSS variables
- **Chat Interface**: User-agent communication with dropdown prompts

---

## Technology Stack

| Technology | Purpose | Version |
|------------|---------|---------|
| **React** | UI Framework | ^19.1.0 |
| **TypeScript** | Type Safety | ^5.9.2 |
| **Vite** | Build Tool | ^6.4.1 |
| **TailwindCSS** | Styling | ^3.4.17 |
| **@xyflow/react** | Graph Visualization | ^12.6.4 |
| **Zustand** | State Management | (via stores) |
| **Axios** | HTTP Client | ^1.13.0 |
| **Lucide React** | Icons | ^0.536.0 |

---

## Project Structure

```
frontend/
├── index.html                 # Entry HTML file
├── package.json               # Dependencies and scripts
├── vite.config.ts             # Vite configuration
├── tailwind.config.js         # TailwindCSS configuration
├── tsconfig.json              # TypeScript configuration
├── postcss.config.js          # PostCSS configuration
├── public/                    # Static assets
└── src/
    ├── main.tsx               # Application entry point
    ├── App.tsx                # Root component
    ├── index.css              # Global styles + CSS variables
    ├── vite-env.d.ts          # Vite type declarations
    ├── assets/                # Images, SVGs, icons
    ├── components/
    │   ├── Chat/              # Chat-related components
    │   │   ├── ChatArea.tsx
    │   │   ├── ChatHeader.tsx
    │   │   ├── Message.tsx
    │   │   ├── UserMessage.tsx
    │   │   ├── GroupCommunicationFeed.tsx
    │   │   ├── AuctionStreamingFeed.tsx
    │   │   └── Prompts/       # Dropdown prompt selectors
    │   ├── MainArea/          # Graph and main content
    │   │   ├── MainArea.tsx
    │   │   ├── ModalContainer.tsx
    │   │   └── Graph/
    │   │       ├── Elements/  # Custom nodes and edges
    │   │       │   ├── CustomNode.tsx
    │   │       │   ├── transportNode.tsx
    │   │       │   ├── CustomEdge.tsx
    │   │       │   └── BranchingEdge.tsx
    │   │       └── Identity/  # Identity modals
    │   ├── Navigation/        # Top navigation bar
    │   └── Sidebar/           # Pattern selection sidebar
    ├── contexts/              # React Context providers
    │   ├── ThemeContext.tsx
    │   └── theme.ts
    ├── hooks/                 # Custom React hooks
    │   ├── useAgentAPI.ts
    │   ├── useChatAreaMeasurement.ts
    │   ├── useTheme.ts
    │   ├── useModalManager.ts
    │   └── useViewportAwareFitView.ts
    ├── stores/                # Zustand stores
    │   ├── auctionStreamingStore.ts
    │   └── groupStreamingStore.ts
    ├── types/                 # TypeScript type definitions
    │   ├── message.ts
    │   └── streaming.ts
    └── utils/                 # Utility functions
        ├── const.ts           # Constants and enums
        ├── graphConfigs.tsx   # Graph node/edge configurations
        ├── patternUtils.ts    # Pattern-related utilities
        ├── retryUtils.ts      # API retry logic
        ├── logger.ts          # Logging utilities
        ├── cn.ts              # Class name utilities
        └── urls.json          # External URL configurations
```

---

## Dependencies

### Production Dependencies

```json
{
  "dependencies": {
    "@radix-ui/react-select": "^2.2.5",
    "@reactflow/node-resizer": "^2.2.14",
    "@xyflow/react": "^12.6.4",
    "axios": "^1.13.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "ldrs": "^1.1.7",
    "lucide-react": "^0.536.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-icons": "^5.5.0",
    "tailwind-merge": "^3.3.1",
    "tailwindcss-animate": "^1.0.7",
    "uuid": "^11.1.0"
  }
}
```

### Key Libraries Explained

| Library | Purpose |
|---------|---------|
| `@xyflow/react` | Interactive graph/flow diagram visualization |
| `zustand` | Lightweight state management (used via imports in stores) |
| `axios` | Promise-based HTTP client for API calls |
| `lucide-react` | Modern icon library |
| `clsx` + `tailwind-merge` | Dynamic class name composition |
| `uuid` | Generate unique IDs for messages |

---

## Configuration Files

### Vite Configuration (`vite.config.ts`)

```typescript
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  server: {
    fs: {
      strict: true,
      allow: [path.resolve(__dirname)],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
    extensions: [".tsx", ".ts", ".jsx", ".js", ".json"],
  },
})
```

### TailwindCSS Configuration (`tailwind.config.js`)

The Tailwind config extends default colors with CSS variable references for theming:

```javascript
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        "app-background": "var(--app-background)",
        "node-background": "var(--node-background)",
        "node-background-hover": "var(--node-background-hover)",
        "node-background-active": "var(--node-background-active)",
        "node-text-primary": "var(--node-text-primary)",
        "accent-primary": "var(--accent-primary)",
        "chat-background": "var(--chat-background)",
        "chat-text": "var(--chat-text)",
        "sidebar-background": "var(--sidebar-background)",
        // ... additional color mappings
      },
      fontFamily: {
        cisco: ["CiscoSans", "Inter"],
        inter: ["Inter"],
      },
      animation: {
        fadeInDropdown: "fadeInDropdown 0.3s ease-out",
        scaleIn: "scaleIn 0.25s ease-in-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

---

## Core Application Architecture

### Entry Point (`main.tsx`)

```typescript
import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App.tsx"
import "./index.css"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

### Root Component (`App.tsx`)

The `App.tsx` is the central orchestrator that:

1. **Manages Pattern Selection**: Tracks which communication pattern is active
2. **Coordinates State**: Bridges streaming stores with UI components
3. **Handles API Communication**: Dispatches queries and handles responses
4. **Controls Animations**: Triggers graph animations on user actions

**Key State Management:**

```typescript
const App: React.FC = () => {
  const { sendMessage } = useAgentAPI()
  
  // Pattern selection
  const [selectedPattern, setSelectedPattern] = useState<PatternType>(
    PATTERNS.GROUP_COMMUNICATION
  )
  
  // Streaming state from Zustand stores
  const startStreaming = useStartGroupStreaming()
  const { connect, reset } = useStreamingActions()
  const status = useStreamingStatus()
  const events = useStreamingEvents()
  
  // UI state
  const [currentUserMessage, setCurrentUserMessage] = useState<string>("")
  const [agentResponse, setAgentResponse] = useState<string>("")
  const [isAgentLoading, setIsAgentLoading] = useState<boolean>(false)
  const [showProgressTracker, setShowProgressTracker] = useState<boolean>(false)
  
  // ...component logic
}
```

**Component Composition:**

```tsx
return (
  <ThemeProvider>
    <div className="flex h-screen w-screen flex-col">
      <Navigation />
      <div className="flex flex-1">
        <Sidebar 
          selectedPattern={selectedPattern}
          onPatternChange={handlePatternChange}
        />
        <div className="flex flex-1 flex-col">
          <MainArea
            pattern={selectedPattern}
            buttonClicked={buttonClicked}
            aiReplied={aiReplied}
            chatHeight={chatHeightValue}
            onNodeHighlight={handleNodeHighlightSetup}
          />
          <ChatArea
            pattern={selectedPattern}
            graphConfig={getGraphConfig(selectedPattern)}
            onDropdownSelect={handleDropdownSelect}
            currentUserMessage={currentUserMessage}
            agentResponse={agentResponse}
            isAgentLoading={isAgentLoading}
            // ...additional props
          />
        </div>
      </div>
    </div>
  </ThemeProvider>
)
```

---

## Component System

### Navigation Component

Top bar with logo, theme toggle, and help button:

```tsx
const Navigation: React.FC = () => {
  const { isLightMode, toggleTheme } = useTheme()
  const [isModalOpen, setIsModalOpen] = useState(false)

  return (
    <div className="h-[52px] w-full border-b border-nav-border bg-nav-background">
      <img src={coffeeAgntcyLogo} alt="Logo" />
      <button onClick={toggleTheme}>
        <ThemeToggleIcon />
      </button>
      <button onClick={() => setIsModalOpen(true)}>
        <HelpCircle />
      </button>
      <InfoModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  )
}
```

### Sidebar Component

Pattern selection with expandable dropdowns:

```tsx
const Sidebar: React.FC<SidebarProps> = ({ selectedPattern, onPatternChange }) => {
  const [isExpanded, setIsExpanded] = useState(true)
  const [transport, setTransport] = useState<string>("")

  useEffect(() => {
    // Fetch transport config from API
    const fetchTransportConfig = async () => {
      const response = await fetch(`${apiUrl}/transport/config`)
      const data = await response.json()
      setTransport(data.transport)
    }
    fetchTransportConfig()
  }, [])

  return (
    <div className="w-64 bg-sidebar-background">
      <SidebarDropdown title="Secure Group Communication">
        <SidebarItem
          title="A2A SLIM"
          isSelected={selectedPattern === PATTERNS.GROUP_COMMUNICATION}
          onClick={() => onPatternChange(PATTERNS.GROUP_COMMUNICATION)}
        />
      </SidebarDropdown>
      <SidebarDropdown title="Publish Subscribe">
        <SidebarItem
          title={`A2A ${transport}`}
          isSelected={selectedPattern === PATTERNS.PUBLISH_SUBSCRIBE}
          onClick={() => onPatternChange(PATTERNS.PUBLISH_SUBSCRIBE)}
        />
      </SidebarDropdown>
    </div>
  )
}
```

### MainArea Component (Graph Visualization)

The heart of the visualization system using ReactFlow:

```tsx
const MainArea: React.FC<MainAreaProps> = ({
  pattern,
  buttonClicked,
  aiReplied,
  chatHeight,
  onNodeHighlight,
}) => {
  const fitViewWithViewport = useViewportAwareFitView()
  const config: GraphConfig = getGraphConfig(pattern)
  
  const [nodes, setNodes, onNodesChange] = useNodesState(config.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(config.edges)

  // Register custom node types
  const nodeTypes = {
    transportNode: TransportNode,
    customNode: CustomNode,
  }
  
  const edgeTypes = {
    custom: CustomEdge,
    branching: BranchingEdge,
  }

  // Animation logic
  useEffect(() => {
    if (buttonClicked && !aiReplied) {
      const animateGraph = async () => {
        for (const step of config.animationSequence) {
          await animate(step.ids, true)  // Highlight on
          await animate(step.ids, false) // Highlight off
        }
      }
      animateGraph()
    }
  }, [buttonClicked, aiReplied])

  return (
    <ReactFlowProvider>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        minZoom={0.15}
        maxZoom={1.8}
      >
        <Controls />
      </ReactFlow>
    </ReactFlowProvider>
  )
}
```

### ChatArea Component

User input and response display:

```tsx
const ChatArea: React.FC<ChatAreaProps> = ({
  pattern,
  onDropdownSelect,
  currentUserMessage,
  agentResponse,
  isAgentLoading,
  showProgressTracker,
  showAuctionStreaming,
}) => {
  const [content, setContent] = useState<string>("")
  const { sendMessageWithCallback } = useAgentAPI()

  const processMessage = async () => {
    if (showAuctionStreaming && onDropdownSelect) {
      onDropdownSelect(content)
    } else {
      await sendMessageWithCallback(content, setMessages, callbacks, pattern)
    }
  }

  return (
    <div className="flex flex-col items-center p-4">
      {currentUserMessage && <UserMessage content={currentUserMessage} />}
      
      {showProgressTracker && (
        <GroupCommunicationFeed
          isVisible={true}
          prompt={currentUserMessage}
        />
      )}
      
      {showAuctionStreaming && (
        <AuctionStreamingFeed
          isVisible={true}
          prompt={currentUserMessage}
        />
      )}
      
      {agentResponse && (
        <div className="flex items-start gap-2">
          <img src={AgentIcon} alt="Agent" />
          <div>{isAgentLoading ? "..." : agentResponse}</div>
        </div>
      )}
      
      <input
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyPress={(e) => e.key === "Enter" && processMessage()}
      />
      <button onClick={processMessage}>Send</button>
    </div>
  )
}
```

---

## State Management

### Zustand Store Pattern

The application uses Zustand for streaming state management. There are two primary stores:

#### 1. Group Streaming Store (`groupStreamingStore.ts`)

Manages SSE-based streaming for group communication:

```typescript
import { create } from "zustand"

interface LogisticsStreamingState {
  events: LogisticsStreamStep[]
  finalResponse: string | null
  isStreaming: boolean
  isComplete: boolean
  error: string | null
  currentOrderId: string | null
}

interface LogisticsStreamingActions {
  addEvent: (event: LogisticsStreamStep) => void
  setFinalResponse: (response: string) => void
  setError: (error: string) => void
  startStreaming: (prompt: string) => Promise<void>
  reset: () => void
}

export const useGroupStreamingStore = create<
  LogisticsStreamingState & LogisticsStreamingActions
>((set) => ({
  events: [],
  finalResponse: null,
  isStreaming: false,
  isComplete: false,
  error: null,

  startStreaming: async (prompt: string) => {
    const { reset, setStreaming, addEvent, setFinalResponse } = 
      useGroupStreamingStore.getState()

    reset()
    setStreaming(true)

    const response = await fetch(`${API_URL}/agent/prompt/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      // Parse NDJSON and add events...
    }
  },

  reset: () => set(initialState),
}))

// Selector hooks for optimized re-renders
export const useGroupEvents = () =>
  useGroupStreamingStore((state) => state.events)

export const useGroupIsStreaming = () =>
  useGroupStreamingStore((state) => state.isStreaming)
```

#### 2. Auction Streaming Store (`auctionStreamingStore.ts`)

Manages streaming for publish/subscribe pattern:

```typescript
interface StreamingState {
  status: "idle" | "connecting" | "streaming" | "completed" | "error"
  error: string | null
  events: AuctionStreamingResponse[]
  abortController: AbortController | null

  connect: (prompt: string) => Promise<void>
  disconnect: () => void
  reset: () => void
}

export const useAuctionStreamingStore = create<StreamingState>((set) => ({
  status: "idle",
  events: [],
  
  connect: async (prompt: string) => {
    const abortController = new AbortController()
    set({ status: "connecting", abortController })

    const response = await fetch(streamingUrl, {
      method: "POST",
      body: JSON.stringify({ prompt }),
      signal: abortController.signal,
    })

    const reader = response.body?.getReader()
    set({ status: "streaming" })

    // Read NDJSON stream...
  },

  disconnect: () => {
    const { abortController } = useAuctionStreamingStore.getState()
    abortController?.abort()
    set({ status: "idle" })
  },
}))
```

---

## API Integration

### useAgentAPI Hook

Central hook for API communication:

```typescript
interface UseAgentAPIReturn {
  loading: boolean
  sendMessage: (prompt: string, pattern?: string) => Promise<string>
  sendMessageWithCallback: (
    prompt: string,
    setMessages: Dispatch<SetStateAction<Message[]>>,
    callbacks?: {
      onStart?: () => void
      onSuccess?: (response: string) => void
      onError?: (error: any) => void
      onRetryAttempt?: (attempt: number, error: Error, nextRetryAt: number) => void
    },
    pattern?: string
  ) => Promise<void>
  cancel: () => void
}

export const useAgentAPI = (): UseAgentAPIReturn => {
  const [loading, setLoading] = useState<boolean>(false)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = async (prompt: string, pattern?: string): Promise<string> => {
    const apiUrl = getApiUrlForPattern(pattern)
    const controller = new AbortController()
    abortRef.current = controller

    const makeApiCall = async () => {
      const response = await axios.post<ApiResponse>(
        `${apiUrl}/agent/prompt`,
        { prompt },
        { signal: controller.signal }
      )
      return response.data.response
    }

    if (shouldEnableRetries(pattern)) {
      return await withRetry(makeApiCall)
    }
    return await makeApiCall()
  }

  const cancel = () => {
    abortRef.current?.abort()
  }

  return { loading, sendMessage, sendMessageWithCallback, cancel }
}
```

### Pattern-Based API Routing

```typescript
// patternUtils.ts
export const PATTERNS = {
  PUBLISH_SUBSCRIBE: "publish_subscribe",
  PUBLISH_SUBSCRIBE_STREAMING: "publish_subscribe_streaming",
  GROUP_COMMUNICATION: "group_communication",
} as const

export const getApiUrlForPattern = (pattern?: string): string => {
  const PUB_SUB_API = import.meta.env.VITE_EXCHANGE_APP_API_URL || "http://127.0.0.1:8000"
  const GROUP_COMM_API = import.meta.env.VITE_LOGISTICS_APP_API_URL || "http://127.0.0.1:9090"

  if (isGroupCommunication(pattern)) {
    return GROUP_COMM_API
  }
  return PUB_SUB_API
}

export const getStreamingEndpointForPattern = (pattern?: string): string => {
  return `${getApiUrlForPattern(pattern)}/agent/prompt/stream`
}
```

### Retry Utilities

```typescript
export const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000,
  backoffMultiplier: 2,
}

export const withRetry = async <T>(
  operation: () => Promise<T>,
  onRetry?: (attempt: number) => void
): Promise<T> => {
  for (let attempt = 1; attempt <= RETRY_CONFIG.maxRetries + 1; attempt++) {
    try {
      return await operation()
    } catch (error) {
      if (attempt > RETRY_CONFIG.maxRetries || !isRetryableError(error)) {
        throw error
      }

      onRetry?.(attempt)
      const delay = RETRY_CONFIG.baseDelay * 
        Math.pow(RETRY_CONFIG.backoffMultiplier, attempt - 1)
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
  throw new Error("Max retries exceeded")
}
```

---

## Graph Visualization System

### Graph Configuration Structure

```typescript
// graphConfigs.tsx
export interface GraphConfig {
  title: string
  nodes: Node[]
  edges: Edge[]
  animationSequence: { ids: string[] }[]
}

export const getGraphConfig = (pattern: string): GraphConfig => {
  switch (pattern) {
    case "publish_subscribe":
      return PUBLISH_SUBSCRIBE_CONFIG
    case "group_communication":
      return GROUP_COMMUNICATION_CONFIG
    default:
      return PUBLISH_SUBSCRIBE_CONFIG
  }
}
```

### Node Configuration Example

```typescript
const GROUP_COMMUNICATION_CONFIG: GraphConfig = {
  title: "Secure Group Communication Network",
  nodes: [
    {
      id: NODE_IDS.LOGISTICS_GROUP,
      type: NODE_TYPES.GROUP,
      data: { label: "Logistics Group" },
      position: { x: 50, y: 50 },
      style: {
        width: 900,
        height: 650,
        backgroundColor: "var(--group-background)",
      },
    },
    {
      id: NODE_IDS.AUCTION_AGENT,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: <SupervisorIcon />,
        label1: "Buyer",
        label2: "Logistics Agent",
        handles: HANDLE_TYPES.SOURCE,
        githubLink: "https://...",
      },
      position: { x: 150, y: 100 },
      parentId: NODE_IDS.LOGISTICS_GROUP,
    },
    // ... more nodes
  ],
  edges: [
    {
      id: EDGE_IDS.SUPERVISOR_TO_TRANSPORT,
      source: NODE_IDS.AUCTION_AGENT,
      target: NODE_IDS.TRANSPORT,
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
    // ... more edges
  ],
  animationSequence: [
    { ids: [NODE_IDS.AUCTION_AGENT] },
    { ids: [EDGE_IDS.SUPERVISOR_TO_TRANSPORT] },
    { ids: [NODE_IDS.TRANSPORT] },
    // ... animation steps
  ],
}
```

### Custom Node Component

```tsx
// CustomNode.tsx
const CustomNode: React.FC<CustomNodeProps> = ({ data }) => {
  const activeClasses = data.active
    ? "bg-node-background-active outline-2 outline-accent-border shadow-lg"
    : "bg-node-background"

  return (
    <div className={`relative flex flex-col rounded-lg p-4 ${activeClasses}`}>
      {/* Icon */}
      <div className="h-5 w-5 rounded bg-node-icon-background">
        {data.icon}
      </div>

      {/* Labels */}
      <span className="text-node-text-primary">{data.label1}</span>
      <span className="text-node-text-secondary text-xs">{data.label2}</span>

      {/* Action buttons */}
      <div className="absolute -right-4 top-1/2 flex flex-col gap-1">
        {data.githubLink && (
          <a href={data.githubLink} target="_blank">
            <img src={githubIcon} alt="GitHub" />
          </a>
        )}
      </div>

      {/* Handles for connections */}
      {(data.handles === "all" || data.handles === "target") && (
        <Handle type="target" position={Position.Top} />
      )}
      {(data.handles === "all" || data.handles === "source") && (
        <Handle type="source" position={Position.Bottom} />
      )}
    </div>
  )
}
```

### Transport Node Component

Circular or rectangular transport node:

```tsx
const TransportNode: React.FC<TransportNodeProps> = ({ data }) => {
  const isCircular = data.compact
  const shapeClasses = isCircular
    ? "h-[120px] w-[120px] rounded-full"
    : "h-[52px] w-[1200px] rounded-lg"

  return (
    <div className={`flex items-center justify-center ${shapeClasses}`}>
      <div className="text-node-text-primary">{data.label}</div>

      {/* Multiple handles for connections */}
      <Handle type="target" id="top" position={Position.Top} />
      <Handle type="source" id="bottom_left" position={Position.Bottom} />
      <Handle type="source" id="bottom_center" position={Position.Bottom} />
      <Handle type="source" id="bottom_right" position={Position.Bottom} />
    </div>
  )
}
```

---

## Theming System

### CSS Variables (`index.css`)

The theming system uses CSS variables that are swapped based on `data-theme` attribute:

```css
:root {
  /* Dark theme (default) */
  --app-background: #23282e;
  --node-background: #373c42;
  --node-background-hover: #4a4f55;
  --node-background-active: #00142b;
  --node-text-primary: #e8e9ea;
  --accent-primary: #187adc;
  --chat-background: #1a2432;
  --chat-text: #fbfcfe;
  --sidebar-background: #23282e;
}

body[data-theme="light"] {
  /* Light theme overrides */
  --app-background: #f5f8fd;
  --node-background: #dee6f9;
  --node-background-hover: #e3eafa;
  --node-background-active: #187adc;
  --node-text-primary: #3c4551;
  --chat-background: #dee6f9;
  --chat-text: #00142b;
  --sidebar-background: #fbfcfe;
}
```

### Theme Context

```typescript
// ThemeContext.tsx
export const ThemeProvider: React.FC = ({ children }) => {
  const [theme, setTheme] = useState<"light" | "dark" | "system">(() => {
    return localStorage.getItem("theme") as any || "dark"
  })

  const [systemTheme, setSystemTheme] = useState<"light" | "dark">("dark")
  const resolvedTheme = theme === "system" ? systemTheme : theme

  useEffect(() => {
    if (resolvedTheme === "light") {
      document.body.setAttribute("data-theme", "light")
    } else {
      document.body.removeAttribute("data-theme")
    }
    localStorage.setItem("theme", theme)
  }, [theme, resolvedTheme])

  const toggleTheme = () => {
    setTheme(resolvedTheme === "light" ? "dark" : "light")
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, isLightMode: resolvedTheme === "light" }}>
      {children}
    </ThemeContext.Provider>
  )
}
```

---

## Types and Interfaces

### Message Type

```typescript
// types/message.ts
export interface Message {
  role: "assistant" | "user"
  content: string
  id: string
  animate: boolean
}
```

### Streaming Types

```typescript
// types/streaming.ts
export interface LogisticsStreamStep {
  order_id: string
  sender: string
  receiver: string
  message: string
  timestamp: string
  state: string
}

export interface AuctionStreamingResponse {
  response: string
}

export interface AuctionStreamingState {
  status: "idle" | "connecting" | "streaming" | "completed" | "error"
  events: AuctionStreamingResponse[]
  error: string | null
}
```

### Graph Element Types

```typescript
// components/MainArea/Graph/Elements/types.ts
export interface CustomNodeData {
  icon: React.ReactNode
  label1: string
  label2: string
  handles: "source" | "target" | "all"
  active?: boolean
  verificationStatus?: "verified" | "failed"
  githubLink?: string
  agentDirectoryLink?: string
  onOpenIdentityModal?: (data: any, position: any, label: string, nodeData: any, isMcp: boolean) => void
}

export interface TransportNodeData {
  label: string
  compact?: boolean
  active?: boolean
  githubLink?: string
}
```

---

## Custom Hooks

### useTheme

```typescript
export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider")
  }
  return context
}
```

### useViewportAwareFitView

```typescript
export const useViewportAwareFitView = () => {
  const { fitView } = useReactFlow()

  return useCallback((options: { chatHeight: number; isExpanded: boolean }) => {
    const padding = options.isExpanded ? 100 : 50
    fitView({
      padding: padding / 100,
      duration: 200,
    })
  }, [fitView])
}
```

### useModalManager

```typescript
export const useModalManager = () => {
  const [activeModal, setActiveModal] = useState<string | null>(null)
  const [activeNodeData, setActiveNodeData] = useState<any>(null)
  const [modalPosition, setModalPosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 })

  const handleOpenIdentityModal = useCallback((data, position, label, nodeData, isMcp) => {
    setActiveModal("identity")
    setActiveNodeData({ ...data, label, isMcp })
    setModalPosition(position)
  }, [])

  const handleCloseModals = useCallback(() => {
    setActiveModal(null)
    setActiveNodeData(null)
  }, [])

  return {
    activeModal,
    activeNodeData,
    modalPosition,
    handleOpenIdentityModal,
    handleCloseModals,
    handlePaneClick: handleCloseModals,
  }
}
```

---

## Adaptation Guide for Agentic Orchestrator

### Key Modifications Required

1. **Replace Graph Configurations**

   Update `graphConfigs.tsx` with your orchestrator's agents:

   ```typescript
   const AGENTIC_ORCHESTRATOR_CONFIG: GraphConfig = {
     title: "Agentic Orchestrator Network",
     nodes: [
       {
         id: "orchestrator",
         type: NODE_TYPES.CUSTOM,
         data: {
           icon: <OrchestratorIcon />,
           label1: "Orchestrator",
           label2: "Central Coordinator",
           handles: HANDLE_TYPES.SOURCE,
         },
         position: { x: 400, y: 100 },
       },
       {
         id: "supply-delivery",
         type: NODE_TYPES.CUSTOM,
         data: {
           icon: <TruckIcon />,
           label1: "Supply Delivery",
           label2: "Delivery Agent",
           handles: HANDLE_TYPES.TARGET,
         },
         position: { x: 200, y: 300 },
       },
       // ... add your agents
     ],
     edges: [/* define connections */],
     animationSequence: [/* define animation order */],
   }
   ```

2. **Update Pattern Definitions**

   Modify `patternUtils.ts`:

   ```typescript
   export const PATTERNS = {
     ORCHESTRATOR_FLOW: "orchestrator_flow",
     AGENT_COLLABORATION: "agent_collaboration",
     // ... your patterns
   } as const
   
   export const getApiUrlForPattern = (pattern?: string): string => {
     const ORCHESTRATOR_API = import.meta.env.VITE_ORCHESTRATOR_API_URL || "http://127.0.0.1:8080"
     return ORCHESTRATOR_API
   }
   ```

3. **Customize Streaming Stores**

   Create stores matching your API response format:

   ```typescript
   interface OrchestratorStreamStep {
     agent_id: string
     action: string
     status: "pending" | "running" | "completed" | "failed"
     message: string
     timestamp: string
   }
   
   export const useOrchestratorStreamingStore = create<...>((set) => ({
     // ...
   }))
   ```

4. **Update Constants**

   Modify `const.ts` with your node/edge identifiers:

   ```typescript
   export const NODE_IDS = {
     ORCHESTRATOR: "orchestrator",
     SUPPLY_DELIVERY: "supply-delivery",
     SUPPLY_INVENTORY: "supply-inventory",
     TRACKING: "tracking",
     NOTIFICATION: "notification",
     TOOLS: "tools",
   } as const
   ```

5. **Replace Assets**

   Update icons and images in `src/assets/` directory.

6. **Environment Variables**

   Create `.env` file:

   ```
   VITE_ORCHESTRATOR_API_URL=http://localhost:8080
   VITE_STREAMING_ENABLED=true
   ```

---

## Step-by-Step Implementation

### Phase 1: Project Setup

1. **Initialize Vite React Project**
   ```bash
   npx create-vite@latest agentic-orchestrator-ui --template react-ts
   cd agentic-orchestrator-ui
   ```

2. **Install Dependencies**
   ```bash
   npm install @xyflow/react axios clsx tailwind-merge lucide-react uuid zustand
   npm install -D tailwindcss postcss autoprefixer @types/uuid tailwindcss-animate
   npx tailwindcss init -p
   ```

3. **Configure Path Aliases**
   
   Update `vite.config.ts` with `@` alias and `tsconfig.json` with path mappings.

### Phase 2: Core Structure

1. Copy and adapt `src/index.css` with CSS variables
2. Set up `src/contexts/` with ThemeContext
3. Create `src/utils/const.ts` with your constants
4. Create `src/types/` with TypeScript interfaces

### Phase 3: State Management

1. Create Zustand stores in `src/stores/`
2. Implement selector hooks for optimized re-renders

### Phase 4: Components

1. **Navigation**: Simple top bar with logo and controls
2. **Sidebar**: Pattern selection menu
3. **MainArea**: ReactFlow graph container
4. **ChatArea**: User input and response display
5. **Graph Elements**: Custom nodes and edges

### Phase 5: API Integration

1. Create `useAgentAPI` hook
2. Implement streaming logic
3. Add retry utilities

### Phase 6: Graph Configuration

1. Define node and edge configurations in `graphConfigs.tsx`
2. Set up animation sequences
3. Create custom node components

### Phase 7: Testing & Refinement

1. Test all patterns
2. Verify streaming functionality
3. Test theme switching
4. Optimize performance

---

## API Contract

The frontend expects the following API endpoints:

| Endpoint | Method | Request Body | Response |
|----------|--------|--------------|----------|
| `/agent/prompt` | POST | `{ prompt: string }` | `{ response: string }` |
| `/agent/prompt/stream` | POST | `{ prompt: string }` | NDJSON stream |
| `/transport/config` | GET | - | `{ transport: string }` |

### Streaming Response Format

```json
{"response": "{'order_id': '123', 'sender': 'Agent1', 'receiver': 'Agent2', 'message': 'Processing...', 'timestamp': '2024-01-01T00:00:00', 'state': 'PROCESSING'}"}
{"response": "{'order_id': '123', 'sender': 'Agent2', 'receiver': 'Agent3', 'message': 'Completed', 'timestamp': '2024-01-01T00:00:01', 'state': 'DELIVERED'}"}
{"response": "Final summary message here"}
```

---

## Conclusion

This guide provides a comprehensive blueprint for replicating the Lungo Frontend. The key architectural decisions are:

1. **Component Composition**: Clear separation between layout, visualization, and interaction components
2. **State Management**: Zustand for global streaming state, React state for local UI state
3. **API Abstraction**: Centralized API hooks with automatic retry logic
4. **Theming**: CSS variables for seamless dark/light mode support
5. **Graph Flexibility**: Configuration-driven node/edge setup for easy customization

By following this guide, you can create a fully functional agentic orchestrator visualization dashboard.
