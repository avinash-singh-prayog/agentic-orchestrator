/**
 * HITL Approval Panel Component
 * 
 * Admin panel for managing Human-in-the-Loop approvals.
 */

import React, { useState, useEffect, useCallback } from "react"
import { Check, X, RefreshCw, AlertCircle, DollarSign, MapPin, Package } from "lucide-react"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import type { HITLInterrupt } from "@/types/streaming"

interface HITLApprovalPanelProps {
    isOpen: boolean
    onClose: () => void
}

const HITLApprovalPanel: React.FC<HITLApprovalPanelProps> = ({ isOpen, onClose }) => {
    const [interrupts, setInterrupts] = useState<HITLInterrupt[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const { getPendingApprovals, approveInterrupt, rejectInterrupt } = useAgentAPI()

    const fetchApprovals = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const pending = await getPendingApprovals()
            setInterrupts(pending)
        } catch (err) {
            setError("Failed to fetch pending approvals")
        } finally {
            setLoading(false)
        }
    }, [getPendingApprovals])

    useEffect(() => {
        if (isOpen) {
            fetchApprovals()
        }
    }, [isOpen, fetchApprovals])

    const handleApprove = async (interruptId: string) => {
        try {
            await approveInterrupt(interruptId)
            setInterrupts((prev) => prev.filter((i) => i.interrupt_id !== interruptId))
        } catch (err) {
            setError("Failed to approve interrupt")
        }
    }

    const handleReject = async (interruptId: string) => {
        try {
            await rejectInterrupt(interruptId, "Rejected by admin")
            setInterrupts((prev) => prev.filter((i) => i.interrupt_id !== interruptId))
        } catch (err) {
            setError("Failed to reject interrupt")
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="w-full max-w-2xl rounded-xl bg-node-background border border-border-color shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between border-b border-border-color p-4">
                    <div className="flex items-center gap-2">
                        <AlertCircle className="h-5 w-5 text-warning" />
                        <h2 className="text-lg font-semibold text-node-text-primary">
                            Pending Approvals
                        </h2>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={fetchApprovals}
                            className="p-2 rounded-lg hover:bg-node-background-hover transition-colors"
                            disabled={loading}
                        >
                            <RefreshCw className={`h-4 w-4 text-node-text-secondary ${loading ? "animate-spin" : ""}`} />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-2 rounded-lg hover:bg-node-background-hover transition-colors"
                        >
                            <X className="h-4 w-4 text-node-text-secondary" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-4 max-h-96 overflow-y-auto">
                    {error && (
                        <div className="mb-4 rounded-lg bg-error/10 border border-error/30 p-3 text-sm text-error">
                            {error}
                        </div>
                    )}

                    {interrupts.length === 0 && !loading && (
                        <div className="text-center py-8 text-node-text-secondary">
                            <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
                            <p>No pending approvals</p>
                        </div>
                    )}

                    <div className="space-y-3">
                        {interrupts.map((interrupt) => (
                            <div
                                key={interrupt.interrupt_id}
                                className="rounded-lg border border-border-color bg-app-background p-4"
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-sm font-medium text-node-text-primary">
                                                Order: {interrupt.order_id}
                                            </span>
                                            <span className="px-2 py-0.5 text-xs rounded-full bg-warning/20 text-warning">
                                                {interrupt.action}
                                            </span>
                                        </div>

                                        <p className="text-sm text-node-text-secondary mb-3">
                                            {interrupt.reason}
                                        </p>

                                        <div className="flex flex-wrap gap-3 text-xs text-node-text-secondary">
                                            {interrupt.context.order_value && (
                                                <div className="flex items-center gap-1">
                                                    <DollarSign className="h-3 w-3" />
                                                    ${interrupt.context.order_value.toLocaleString()}
                                                </div>
                                            )}
                                            {interrupt.context.origin && (
                                                <div className="flex items-center gap-1">
                                                    <MapPin className="h-3 w-3" />
                                                    {interrupt.context.origin} → {interrupt.context.destination}
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex gap-2 ml-4">
                                        <button
                                            onClick={() => handleApprove(interrupt.interrupt_id)}
                                            className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-success/20 text-success hover:bg-success/30 transition-colors"
                                        >
                                            <Check className="h-4 w-4" />
                                            Approve
                                        </button>
                                        <button
                                            onClick={() => handleReject(interrupt.interrupt_id)}
                                            className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-error/20 text-error hover:bg-error/30 transition-colors"
                                        >
                                            <X className="h-4 w-4" />
                                            Reject
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default HITLApprovalPanel
