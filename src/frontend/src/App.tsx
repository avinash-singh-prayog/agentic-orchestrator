/**
 * App Component
 * 
 * Root component with premium UI layout including chat history sidebar
 * and draggable resizers between panels.
 */

import React, { useState, useEffect, useCallback, useRef } from "react"

import Navigation from "@/components/Navigation/Navigation"
import { ChatArea } from "@/components/Chat"
import ChatSidebar from "@/components/Chat/ChatSidebar"
import AuthScreen from "@/components/Auth/AuthScreen"
import { Loader2 } from "lucide-react"

import {
  useStreamingStatus,
  useStreamingEvents,
  useStreamingFinalResponse
} from "@/stores/orchestratorStreamingStore"
import { useChatHistoryStore, useChatSession } from "@/stores/chatHistoryStore"

const App: React.FC = () => {

  const [sidebarWidth, setSidebarWidth] = useState(220) // Sidebar width in pixels
  const [draggingPanel, setDraggingPanel] = useState<'sidebar' | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const streamingStatus = useStreamingStatus()
  const streamingEvents = useStreamingEvents()
  const finalResponse = useStreamingFinalResponse()
  const addAssistantMessage = useChatHistoryStore(state => state.addAssistantMessage)
  const isLoadingSession = useChatHistoryStore(state => state.isLoading)

  // Auth & Session
  const { isAuthenticated } = useChatSession()
  const initSession = useChatHistoryStore(state => state.initSession)
  // Initialize session on mount
  useEffect(() => {
    initSession()
  }, [initSession])

  // Responsive Layout Handler
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      if (width < 768) {
        setSidebarWidth(50) // Collapse sidebar
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

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
      
      addAssistantMessage(finalResponse, activity)
    }
  }, [streamingStatus, finalResponse, streamingEvents, addAssistantMessage])

  // Handle resizer drag
  const handleSidebarMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setDraggingPanel('sidebar')
  }, [])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!draggingPanel || !containerRef.current) return
    if (draggingPanel !== 'sidebar') return
    const containerRect = containerRef.current.getBoundingClientRect()
    const newWidth = e.clientX - containerRect.left
    const minWidth = 180
    const maxWidth = 350
    setSidebarWidth(Math.max(minWidth, Math.min(maxWidth, newWidth)))
  }, [draggingPanel])

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
    background: "var(--bg-app)",
  }


  const getResizerStyles = (isActive: boolean): React.CSSProperties => ({
    width: 6,
    cursor: 'col-resize',
    background: isActive
      ? 'linear-gradient(180deg, rgba(99, 102, 241, 0.5) 0%, rgba(139, 92, 246, 0.5) 100%)'
      : 'transparent',
    borderLeft: '1px solid var(--border-subtle)',
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
    background: 'var(--border-hover)',
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

  if (isLoadingSession) {
    return (
      <div style={{ ...appStyles, alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 className="animate-spin text-[var(--accent-primary)]" size={32} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <AuthScreen />
  }

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
          minWidth: 300,
          background: "var(--bg-app)",
          flexShrink: 0,
        }}>
          <ChatArea />
        </div>
      </div>

    </div>
  )
}

export default App
