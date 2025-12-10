/**
 * Navigation Component
 * 
 * Top navigation bar with logo, theme toggle, and status.
 */

import React, { useState, useEffect } from "react"
import { Sun, Moon, Activity, AlertCircle } from "lucide-react"
import { useTheme } from "@/contexts/ThemeContext"
import { useAgentAPI } from "@/hooks/useAgentAPI"

const Navigation: React.FC = () => {
    const { isLightMode, toggleTheme } = useTheme()
    const { getHealth } = useAgentAPI()
    const [healthStatus, setHealthStatus] = useState<"healthy" | "unhealthy" | "loading">("loading")

    useEffect(() => {
        const checkHealth = async () => {
            try {
                await getHealth()
                setHealthStatus("healthy")
            } catch {
                setHealthStatus("unhealthy")
            }
        }

        checkHealth()
        const interval = setInterval(checkHealth, 30000)
        return () => clearInterval(interval)
    }, [getHealth])

    return (
        <nav className="flex h-14 w-full items-center justify-between border-b border-nav-border bg-nav-background px-6">
            {/* Logo and Title */}
            <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-primary">
                    <span className="text-lg font-bold text-white">🚚</span>
                </div>
                <div className="flex flex-col">
                    <span className="text-sm font-semibold text-node-text-primary">
                        Logistics Orchestrator
                    </span>
                    <span className="text-xs text-node-text-secondary">
                        Multi-Agent System
                    </span>
                </div>
            </div>

            {/* Right side controls */}
            <div className="flex items-center gap-4">
                {/* Health Status */}
                <div className="flex items-center gap-2">
                    {healthStatus === "healthy" ? (
                        <Activity className="h-4 w-4 text-success" />
                    ) : healthStatus === "unhealthy" ? (
                        <AlertCircle className="h-4 w-4 text-error" />
                    ) : (
                        <Activity className="h-4 w-4 animate-pulse text-node-text-secondary" />
                    )}
                    <span className="text-xs text-node-text-secondary">
                        {healthStatus === "healthy"
                            ? "Connected"
                            : healthStatus === "unhealthy"
                                ? "Disconnected"
                                : "Checking..."}
                    </span>
                </div>

                {/* Theme Toggle */}
                <button
                    onClick={toggleTheme}
                    className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-color bg-node-background transition-colors hover:bg-node-background-hover"
                    aria-label="Toggle theme"
                >
                    {isLightMode ? (
                        <Moon className="h-4 w-4 text-node-text-primary" />
                    ) : (
                        <Sun className="h-4 w-4 text-node-text-primary" />
                    )}
                </button>
            </div>
        </nav>
    )
}

export default Navigation
