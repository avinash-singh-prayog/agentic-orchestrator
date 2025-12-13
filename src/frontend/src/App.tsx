/**
 * App Component
 * 
 * Root component with premium UI layout.
 */

import React, { useState, useEffect } from "react"
import { ThemeProvider } from "@/contexts/ThemeContext"
import Navigation from "@/components/Navigation/Navigation"
import MainArea from "@/components/MainArea/MainArea"
import { ChatArea } from "@/components/Chat"
import HITLApprovalPanel from "@/components/Admin/HITLApprovalPanel"
import { ClipboardCheck } from "lucide-react"
import { useStreamingStatus, useStreamingEvents } from "@/stores/orchestratorStreamingStore"

const App: React.FC = () => {
  const [showHITLPanel, setShowHITLPanel] = useState(false)
  const [syncActiveAgent, setSyncActiveAgent] = useState<string | null>(null)

  const streamingStatus = useStreamingStatus()
  const streamingEvents = useStreamingEvents()

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

  const appStyles: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    width: "100vw",
    overflow: "hidden",
    background: "linear-gradient(135deg, #0a0a0f 0%, #12121a 50%, #0a0a0f 100%)",
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
    background: "linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(249, 115, 22, 0.15))",
    border: "1px solid rgba(245, 158, 11, 0.3)",
    color: "#fbbf24",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.2s ease",
    boxShadow: "0 4px 15px rgba(0, 0, 0, 0.2)",
  }

  return (
    <ThemeProvider>
      <div style={appStyles}>
        <Navigation />

        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {/* Chat area - LEFT (35%) */}
          <div style={{
            width: "35%",
            borderRight: "1px solid rgba(255, 255, 255, 0.08)",
            background: "rgba(15, 15, 21, 0.9)",
          }}>
            <ChatArea onAgentActive={setSyncActiveAgent} />
          </div>

          {/* Graph - RIGHT (65%) */}
          <div style={{
            position: "relative",
            width: "65%",
            background: "linear-gradient(180deg, rgba(10, 10, 15, 1) 0%, rgba(15, 15, 21, 1) 100%)",
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
