/**
 * App Component
 * 
 * Root component that assembles the application layout.
 */

import React, { useState } from "react"
import { ThemeProvider } from "@/contexts/ThemeContext"
import Navigation from "@/components/Navigation/Navigation"
import MainArea from "@/components/MainArea/MainArea"
import { ChatArea } from "@/components/Chat"
import HITLApprovalPanel from "@/components/Admin/HITLApprovalPanel"
import { ClipboardCheck } from "lucide-react"

const App: React.FC = () => {
  const [isProcessing, setIsProcessing] = useState(false)
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null)
  const [showHITLPanel, setShowHITLPanel] = useState(false)

  const handleProcessingChange = (processing: boolean) => {
    setIsProcessing(processing)
    if (processing) {
      // Simulate node activation sequence
      setActiveNodeId("supervisor")
    } else {
      setActiveNodeId(null)
    }
  }

  return (
    <ThemeProvider>
      <div className="flex h-screen w-screen flex-col bg-app-background">
        {/* Navigation */}
        <Navigation />

        {/* Main content area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Graph visualization - 60% width */}
          <div className="relative w-[60%] border-r border-border-color">
            <MainArea isProcessing={isProcessing} activeNodeId={activeNodeId} />

            {/* HITL button overlay */}
            <button
              onClick={() => setShowHITLPanel(true)}
              className="absolute bottom-4 right-4 flex items-center gap-2 px-4 py-2 rounded-lg bg-node-background border border-border-color text-sm text-node-text-primary hover:bg-node-background-hover transition-colors shadow-lg"
            >
              <ClipboardCheck className="h-4 w-4 text-warning" />
              HITL Approvals
            </button>
          </div>

          {/* Chat area - 40% width */}
          <div className="w-[40%]">
            <ChatArea onProcessingChange={handleProcessingChange} />
          </div>
        </div>

        {/* HITL Modal */}
        <HITLApprovalPanel
          isOpen={showHITLPanel}
          onClose={() => setShowHITLPanel(false)}
        />
      </div>
    </ThemeProvider>
  )
}

export default App
