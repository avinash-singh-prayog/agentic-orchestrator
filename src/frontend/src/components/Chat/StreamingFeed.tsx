/**
 * Streaming Feed Component
 * 
 * Real-time display of streaming events from the orchestrator.
 */

import React from "react"
import { Brain, MapPin, CircleDollarSign, Package, Zap, CheckCircle, AlertCircle, Loader2 } from "lucide-react"
import {
    useStreamingEvents,
    useStreamingStatus,
    useStreamingFinalResponse,
} from "@/stores/orchestratorStreamingStore"

const agentIcons: Record<string, React.FC<{ className?: string }>> = {
    supervisor: Brain,
    serviceability: MapPin,
    rate: CircleDollarSign,
    carrier: Package,
    slim: Zap,
}

const stateColors: Record<string, string> = {
    PROCESSING: "text-accent-primary",
    COMPLETED: "text-success",
    PENDING_APPROVAL: "text-warning",
    ERROR: "text-error",
}

const StreamingFeed: React.FC = () => {
    const events = useStreamingEvents()
    const status = useStreamingStatus()
    const finalResponse = useStreamingFinalResponse()

    if (status === "idle") {
        return null
    }

    return (
        <div className="space-y-3">
            {/* Connection status */}
            {status === "connecting" && (
                <div className="flex items-center gap-2 text-node-text-secondary">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Connecting to orchestrator...</span>
                </div>
            )}

            {/* Events list */}
            {events.map((event, index) => {
                const Icon = agentIcons[event.sender.toLowerCase()] || Brain
                const stateColor = stateColors[event.state] || "text-node-text-secondary"

                return (
                    <div
                        key={index}
                        className="flex items-start gap-3 rounded-lg border border-border-color bg-node-background p-3 animate-scaleIn"
                    >
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-primary/20">
                            <Icon className={`h-4 w-4 ${stateColor}`} />
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-node-text-primary capitalize">
                                    {event.sender}
                                </span>
                                <span className={`text-xs ${stateColor}`}>
                                    {event.state === "COMPLETED" && <CheckCircle className="inline h-3 w-3 mr-1" />}
                                    {event.state === "ERROR" && <AlertCircle className="inline h-3 w-3 mr-1" />}
                                    {event.state}
                                </span>
                            </div>
                            <p className="mt-1 text-sm text-node-text-secondary">{event.message}</p>
                        </div>
                    </div>
                )
            })}

            {/* Final response */}
            {finalResponse && status === "completed" && (
                <div className="rounded-lg border border-success/30 bg-success/10 p-4">
                    <div className="flex items-center gap-2 mb-2">
                        <CheckCircle className="h-4 w-4 text-success" />
                        <span className="text-sm font-medium text-success">Response</span>
                    </div>
                    <p className="text-sm text-node-text-primary whitespace-pre-wrap">
                        {finalResponse}
                    </p>
                </div>
            )}

            {/* Error state */}
            {status === "error" && (
                <div className="rounded-lg border border-error/30 bg-error/10 p-4">
                    <div className="flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-error" />
                        <span className="text-sm font-medium text-error">
                            An error occurred while processing your request.
                        </span>
                    </div>
                </div>
            )}
        </div>
    )
}

export default StreamingFeed
