/**
 * App Component
 * 
 * Root component with premium UI layout including chat history sidebar
 * and draggable resizers between panels.
 */

import React, { useState, useEffect, useCallback, useRef } from "react"
import { ThemeProvider } from "@/contexts/ThemeContext"
import Navigation from "@/components/Navigation/Navigation"
import MainArea from "@/components/MainArea/MainArea"
import { ChatArea } from "@/components/Chat"
import ChatSidebar from "@/components/Chat/ChatSidebar"
import HITLApprovalPanel from "@/components/Admin/HITLApprovalPanel"
import { ClipboardCheck } from "lucide-react"
import {
  useStreamingStatus,
  useStreamingEvents,
  useStreamingFinalResponse
} from "@/stores/orchestratorStreamingStore"
import { useChatHistoryStore } from "@/stores/chatHistoryStore"

const App: React.FC = () => {
  const [showHITLPanel, setShowHITLPanel] = useState(false)
  const [syncActiveAgent, setSyncActiveAgent] = useState<string | null>(null)
  const [sidebarWidth, setSidebarWidth] = useState(220) // Sidebar width in pixels
  const [chatWidth, setChatWidth] = useState(400) // Chat width in pixels
  const [draggingPanel, setDraggingPanel] = useState<'sidebar' | 'chat' | null>(null)
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

  const handleChatMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setDraggingPanel('chat')
  }, [])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!draggingPanel || !containerRef.current) return

    const containerRect = containerRef.current.getBoundingClientRect()

    if (draggingPanel === 'sidebar') {
      const newWidth = e.clientX - containerRect.left
      const minWidth = 180
      const maxWidth = 350
      setSidebarWidth(Math.max(minWidth, Math.min(maxWidth, newWidth)))
    } else if (draggingPanel === 'chat') {
      const newWidth = e.clientX - containerRect.left - sidebarWidth
      const minWidth = 300
      const maxWidth = containerRect.width - sidebarWidth - 400
      setChatWidth(Math.max(minWidth, Math.min(maxWidth, newWidth)))
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
    background: "linear-gradient(135deg, #14161e 0%, #1a1d28 50%, #14161e 100%)",
  }

  const hitlButtonStyles: React.CSSProperties = {
    position: "absolute",
    bottom: 24,
    right: 24,
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 16px",
    borderRadius: 12,
    background: "linear-gradient(135deg, rgba(251, 191, 36, 0.12), rgba(251, 146, 60, 0.12))",
    border: "1px solid rgba(251, 191, 36, 0.25)",
    color: "#fbbf24",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.2s ease",
    boxShadow: "0 4px 15px rgba(0, 0, 0, 0.2)",
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
    <ThemeProvider>
      <div style={appStyles}>
        <Navigation />

        <div ref={containerRef} style={{ display: "flex", flex: 1, overflow: "hidden" }}>
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
            width: chatWidth,
            minWidth: 300,
            background: "rgba(20, 22, 30, 0.95)",
            flexShrink: 0,
          }}>
            <ChatArea onAgentActive={setSyncActiveAgent} />
          </div>

          {/* Chat Resizer */}
          <Resizer
            onMouseDown={handleChatMouseDown}
            isActive={draggingPanel === 'chat'}
          />

          {/* Graph - RIGHT */}
          <div style={{
            position: "relative",
            flex: 1,
            minWidth: 400,
            background: "linear-gradient(180deg, rgba(20, 22, 30, 1) 0%, rgba(26, 29, 40, 1) 100%)",
          }}>
            <MainArea
              isProcessing={isProcessing}
              activeAgent={streamingActiveAgent || syncActiveAgent}
            />

            <button onClick={() => setShowHITLPanel(true)} style={hitlButtonStyles}>
              <ClipboardCheck style={{ width: 16, height: 16 }} />
              HITL Approvals
            </button>
          </div>
        </div>

        <HITLApprovalPanel isOpen={showHITLPanel} onClose={() => setShowHITLPanel(false)} />
      </div>
    </ThemeProvider>
  )
}

export default App
