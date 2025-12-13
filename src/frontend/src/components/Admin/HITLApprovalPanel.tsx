/**
 * HITL Approval Panel Component
 * 
 * Premium styled modal for Human-in-the-Loop approvals.
 */

import React, { useState, useEffect } from "react"
import { X, Check, XCircle, Loader2, AlertTriangle, Clock, Package } from "lucide-react"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import type { HITLInterrupt } from "@/types/streaming"

interface HITLApprovalPanelProps {
    isOpen: boolean
    onClose: () => void
}

const HITLApprovalPanel: React.FC<HITLApprovalPanelProps> = ({
    isOpen,
    onClose,
}) => {
    const [pendingApprovals, setPendingApprovals] = useState<HITLInterrupt[]>([])
    const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set())
    const { getPendingApprovals, approveInterrupt, rejectInterrupt } = useAgentAPI()

    useEffect(() => {
        if (isOpen) {
            loadApprovals()
        }
    }, [isOpen])

    const loadApprovals = async () => {
        try {
            const approvals = await getPendingApprovals()
            setPendingApprovals(approvals)
        } catch (error) {
            console.error("Failed to load approvals", error)
        }
    }

    const handleApprove = async (id: string) => {
        setLoadingIds((prev) => new Set(prev).add(id))
        try {
            await approveInterrupt(id)
            setPendingApprovals((prev) => prev.filter((a) => a.interrupt_id !== id))
        } catch (error) {
            console.error("Failed to approve", error)
        } finally {
            setLoadingIds((prev) => {
                const next = new Set(prev)
                next.delete(id)
                return next
            })
        }
    }

    const handleReject = async (id: string) => {
        setLoadingIds((prev) => new Set(prev).add(id))
        try {
            await rejectInterrupt(id, "Rejected by admin")
            setPendingApprovals((prev) => prev.filter((a) => a.interrupt_id !== id))
        } catch (error) {
            console.error("Failed to reject", error)
        } finally {
            setLoadingIds((prev) => {
                const next = new Set(prev)
                next.delete(id)
                return next
            })
        }
    }

    if (!isOpen) return null

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={onClose}
        >
            <div
                className="w-full max-w-2xl max-h-[80vh] overflow-hidden rounded-2xl border border-white/10 bg-slate-900/95 backdrop-blur-xl shadow-2xl fade-in-up"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30">
                            <AlertTriangle className="h-5 w-5 text-amber-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-white">HITL Approvals</h2>
                            <p className="text-sm text-slate-400">
                                {pendingApprovals.length} pending approval{pendingApprovals.length !== 1 ? "s" : ""}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="max-h-[60vh] overflow-y-auto p-6">
                    {pendingApprovals.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-800/50 border border-white/5 mb-4">
                                <Check className="h-8 w-8 text-emerald-400" />
                            </div>
                            <h3 className="text-lg font-medium text-white mb-2">All Clear!</h3>
                            <p className="text-sm text-slate-400">No pending approvals at the moment.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {pendingApprovals.map((approval) => {
                                const isLoading = loadingIds.has(approval.interrupt_id)

                                return (
                                    <div
                                        key={approval.interrupt_id}
                                        className="rounded-xl border border-white/10 bg-slate-800/50 p-5"
                                    >
                                        {/* Order info header */}
                                        <div className="flex items-start justify-between mb-4">
                                            <div className="flex items-center gap-3">
                                                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/30">
                                                    <Package className="h-5 w-5 text-purple-400" />
                                                </div>
                                                <div>
                                                    <div className="text-sm font-medium text-white">
                                                        Order #{approval.context?.order_id || "N/A"}
                                                    </div>
                                                    <div className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                                                        <Clock className="h-3 w-3" />
                                                        Awaiting approval
                                                    </div>
                                                </div>
                                            </div>
                                            <span className="px-3 py-1 text-xs font-medium text-amber-400 bg-amber-500/20 border border-amber-500/30 rounded-full">
                                                High Value
                                            </span>
                                        </div>

                                        {/* Details */}
                                        <div className="space-y-2 mb-4">
                                            <p className="text-sm text-slate-300 leading-relaxed">
                                                {approval.reason || "This order requires manual approval due to its value."}
                                            </p>
                                            {approval.context?.order_value && (
                                                <div className="flex items-center gap-2 text-sm">
                                                    <span className="text-slate-400">Order Value:</span>
                                                    <span className="font-medium text-white">
                                                        ${approval.context.order_value.toLocaleString()}
                                                    </span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Actions */}
                                        <div className="flex items-center gap-3">
                                            <button
                                                onClick={() => handleApprove(approval.interrupt_id)}
                                                disabled={isLoading}
                                                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-sm font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50"
                                            >
                                                {isLoading ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <>
                                                        <Check className="h-4 w-4" />
                                                        Approve
                                                    </>
                                                )}
                                            </button>
                                            <button
                                                onClick={() => handleReject(approval.interrupt_id)}
                                                disabled={isLoading}
                                                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border border-red-500/30 bg-red-500/10 text-sm font-medium text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50"
                                            >
                                                {isLoading ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <>
                                                        <XCircle className="h-4 w-4" />
                                                        Reject
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default HITLApprovalPanel
