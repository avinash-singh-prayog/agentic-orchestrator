/**
 * App Component
 * 
 * Root component with premium UI layout including chat history sidebar
 * and draggable resizers between panels.
 */

import React, { useState, useEffect, useCallback, useRef } from "react"
import { useTheme } from "@/contexts/ThemeContext"
import Navigation from "@/components/Navigation/Navigation"
import MainArea from "@/components/MainArea/MainArea"
import { ChatArea } from "@/components/Chat"
import ChatSidebar from "@/components/Chat/ChatSidebar"
import { ChevronLeft, ChevronRight } from "lucide-react"
import {
  useStreamingStatus,
  useStreamingEvents,
  useStreamingFinalResponse
} from "@/stores/orchestratorStreamingStore"
import { useChatHistoryStore } from "@/stores/chatHistoryStore"

const App: React.FC = () => {
  const { isLightMode } = useTheme()
  const [isGraphVisible, setIsGraphVisible] = useState(false)
  const [syncActiveAgent, setSyncActiveAgent] = useState<string | null>(null)
  const [sidebarWidth, setSidebarWidth] = useState(220) // Sidebar width in pixels
  const [graphWidth, setGraphWidth] = useState(450) // Graph width in pixels
  const [draggingPanel, setDraggingPanel] = useState<'sidebar' | 'graph' | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const streamingStatus = useStreamingStatus()
  const streamingEvents = useStreamingEvents()
  const finalResponse = useStreamingFinalResponse()
  const addAssistantMessage = useChatHistoryStore(state => state.addAssistantMessage)

  const isProcessing = streamingStatus === "streaming" || streamingStatus === "connecting"

  // Get current active agent from streaming events
  const streamingActiveAgent = streamingEvents.length > 0
    ? streamingEvents[streamingEvents.length - 1].sender
    : null

  // Clear sync active agent when not processing
  useEffect(() => {
    if (streamingStatus === "idle") {
      setSyncActiveAgent(null)
    }
  }, [streamingStatus])

  // Save assistant response to history when streaming completes
  useEffect(() => {
    if (streamingStatus === "completed" && finalResponse) {
      // Convert streaming events to activity format and save with message
      const activity = streamingEvents.map(event => ({
        sender: event.sender,
        receiver: event.receiver,
        message: event.message,
        state: event.state
      }))
      console.log('[Activity Save] Saving activity with', activity.length, 'events:', activity)
      addAssistantMessage(finalResponse, activity)
    }
  }, [streamingStatus, finalResponse, streamingEvents, addAssistantMessage])

  // Handle resizer drag
  const handleSidebarMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setDraggingPanel('sidebar')
  }, [])

  const handleGraphMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setDraggingPanel('graph')
  }, [])


  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!draggingPanel || !containerRef.current) return

    const containerRect = containerRef.current.getBoundingClientRect()

    if (draggingPanel === 'sidebar') {
      const newWidth = e.clientX - containerRect.left
      const minWidth = 180
      const maxWidth = 350
      setSidebarWidth(Math.max(minWidth, Math.min(maxWidth, newWidth)))
    } else if (draggingPanel === 'graph') {
      const newWidth = containerRect.right - e.clientX
      const minWidth = 300
      const maxWidth = containerRect.width - sidebarWidth - 300 // Keep space for chat
      setGraphWidth(Math.max(minWidth, Math.min(maxWidth, newWidth)))
    }
  }, [draggingPanel, sidebarWidth])

  const handleMouseUp = useCallback(() => {
    setDraggingPanel(null)
  }, [])

  // Add/remove mouse event listeners
  useEffect(() => {
    if (draggingPanel) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    } else {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [draggingPanel, handleMouseMove, handleMouseUp])

  const appStyles: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    width: "100vw",
    overflow: "hidden",
    background: isLightMode
      ? "#f8fafc"
      : "linear-gradient(135deg, #14161e 0%, #1a1d28 50%, #14161e 100%)",
  }


  const getResizerStyles = (isActive: boolean): React.CSSProperties => ({
    width: 6,
    cursor: 'col-resize',
    background: isActive
      ? 'linear-gradient(180deg, rgba(99, 102, 241, 0.5) 0%, rgba(139, 92, 246, 0.5) 100%)'
      : 'transparent',
    borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
    transition: isActive ? 'none' : 'background 0.2s ease',
    position: 'relative',
    zIndex: 10,
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  })

  const resizerHandleStyles: React.CSSProperties = {
    width: 4,
    height: 40,
    borderRadius: 2,
    background: 'rgba(255, 255, 255, 0.3)',
  }

  const Resizer: React.FC<{ onMouseDown: (e: React.MouseEvent) => void; isActive: boolean }> = ({ onMouseDown, isActive }) => (
    <div
      style={getResizerStyles(isActive)}
      onMouseDown={onMouseDown}
      onMouseEnter={(e) => {
        if (!draggingPanel) {
          (e.currentTarget as HTMLDivElement).style.background =
            'linear-gradient(180deg, rgba(99, 102, 241, 0.3) 0%, rgba(139, 92, 246, 0.3) 100%)'
        }
      }}
      onMouseLeave={(e) => {
        if (!draggingPanel) {
          (e.currentTarget as HTMLDivElement).style.background = 'transparent'
        }
      }}
    >
      <div style={resizerHandleStyles} />
    </div>
  )

  return (
    <div style={appStyles}>
      <Navigation />

      <div ref={containerRef} style={{ display: "flex", flex: 1, overflow: "hidden", position: "relative" }}>
        {/* Sidebar - Chat History */}
        <div style={{ width: sidebarWidth > 50 ? sidebarWidth : 50, flexShrink: 0 }}>
          <ChatSidebar
            isCollapsed={sidebarWidth <= 50}
            onToggleCollapse={() => setSidebarWidth(sidebarWidth <= 50 ? 220 : 50)}
          />
        </div>

        {/* Sidebar Resizer */}
        <Resizer
          onMouseDown={handleSidebarMouseDown}
          isActive={draggingPanel === 'sidebar'}
        />

        {/* Chat area */}
        <div style={{
          flex: 1,
          // width: isGraphVisible ? `calc(100% - ${graphWidth}px)` : "100%",
          marginRight: isGraphVisible ? graphWidth : 0,
          minWidth: 300,
          background: isLightMode ? "#ffffff" : "rgba(20, 22, 30, 0.95)",
          flexShrink: 0,
          transition: draggingPanel === 'graph' ? "none" : "margin-right 0.3s ease",
          borderRight: "none",
        }}>
          <ChatArea onAgentActive={setSyncActiveAgent} />
        </div>


        {/* Graph - RIGHT (Collapsible) */}
        {/* Graph - RIGHT (Collapsible) */}
        <div style={{
          position: "absolute",
          right: 0,
          top: 0,
          bottom: 0,
          width: isGraphVisible ? graphWidth : 0,
          overflow: "hidden",
          transition: draggingPanel === 'graph' ? "none" : "width 0.3s ease",
          background: isLightMode
            ? "#f1f5f9"
            : "linear-gradient(180deg, rgba(20, 22, 30, 1) 0%, rgba(26, 29, 40, 1) 100%)",
          borderLeft: "none",
        }}>
          {isGraphVisible && (
            <MainArea
              isProcessing={isProcessing}
              activeAgent={streamingActiveAgent || syncActiveAgent}
            />
          )}

          {/* Graph Resizer (Invisible/Hoverable) */}
          {isGraphVisible && (
            <div
              onMouseDown={handleGraphMouseDown}
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                bottom: 0,
                width: 6,
                cursor: "col-resize",
                zIndex: 50,
                transform: "translateX(-50%)", // Center on the edge
              }}
              onMouseEnter={(e) => {
                if (!draggingPanel) {
                  e.currentTarget.style.background = 'rgba(79, 143, 255, 0.5)'
                }
              }}
              onMouseLeave={(e) => {
                if (!draggingPanel) {
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            />
          )}
        </div>

        {/* Toggle Button (Arrow) */}
        <div
          onClick={() => setIsGraphVisible(!isGraphVisible)}
          style={{
            position: "absolute",
            right: isGraphVisible ? graphWidth : 0,
            top: 20,
            // transform: "translateY(-50%)",
            width: 24,
            height: 40,
            background: isLightMode ? "#f1f5f9" : "#1a1d28",
            border: isLightMode ? "1px solid #e2e8f0" : "1px solid rgba(255, 255, 255, 0.1)",
            borderRight: "none",
            borderTopLeftRadius: 8,
            borderBottomLeftRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            zIndex: 100,
            transition: draggingPanel === 'graph' ? "none" : "right 0.3s ease",
            boxShadow: isLightMode ? "-2px 0 8px rgba(0,0,0,0.05)" : "-2px 0 8px rgba(0,0,0,0.3)",
          }}
          title={isGraphVisible ? "Collapse Architecture" : "View Architecture"}
        >
          {isGraphVisible ? (
            <ChevronRight size={16} color={isLightMode ? "#64748b" : "#94a3b8"} />
          ) : (
            <ChevronLeft size={16} color={isLightMode ? "#64748b" : "#94a3b8"} />
          )}
        </div>
      </div>
    </div>
  )
}

export default App
