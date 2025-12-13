/**
 * Navigation Component
 * 
 * Premium styled navigation with inline styles.
 */

import React, { useState, useEffect } from "react"
import { Sun, Moon, Activity, AlertCircle, Boxes } from "lucide-react"
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

    const navStyles: React.CSSProperties = {
        height: 64,
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
        background: "linear-gradient(90deg, rgba(10, 10, 15, 0.98), rgba(18, 18, 26, 0.95))",
        borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        backdropFilter: "blur(20px)",
    }

    const logoBoxStyles: React.CSSProperties = {
        width: 44,
        height: 44,
        borderRadius: 12,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
        boxShadow: "0 4px 15px rgba(59, 130, 246, 0.3)",
    }

    const healthBadgeStyles: React.CSSProperties = {
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 14px",
        borderRadius: 20,
        background: "rgba(30, 32, 48, 0.8)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
    }

    const buttonStyles: React.CSSProperties = {
        width: 44,
        height: 44,
        borderRadius: 12,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(30, 32, 48, 0.6)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        cursor: "pointer",
        transition: "all 0.2s ease",
    }

    return (
        <nav style={navStyles}>
            {/* Logo */}
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <div style={logoBoxStyles}>
                    <Boxes style={{ width: 22, height: 22, color: "white" }} />
                </div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                    <span style={{
                        fontSize: 16,
                        fontWeight: 700,
                        background: "linear-gradient(135deg, #3b82f6, #a78bfa)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                    }}>
                        Logistics Orchestrator
                    </span>
                    <span style={{ fontSize: 11, color: "#64748b" }}>
                        Multi-Agent System
                    </span>
                </div>
            </div>

            {/* Right side */}
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                {/* Health Status */}
                <div style={healthBadgeStyles}>
                    {healthStatus === "healthy" ? (
                        <>
                            <Activity style={{ width: 16, height: 16, color: "#10b981" }} />
                            <span style={{ fontSize: 12, fontWeight: 500, color: "#10b981" }}>Connected</span>
                        </>
                    ) : healthStatus === "unhealthy" ? (
                        <>
                            <AlertCircle style={{ width: 16, height: 16, color: "#ef4444" }} />
                            <span style={{ fontSize: 12, fontWeight: 500, color: "#ef4444" }}>Disconnected</span>
                        </>
                    ) : (
                        <>
                            <Activity style={{ width: 16, height: 16, color: "#94a3b8" }} />
                            <span style={{ fontSize: 12, fontWeight: 500, color: "#94a3b8" }}>Checking...</span>
                        </>
                    )}
                </div>

                {/* Theme Toggle */}
                <button onClick={toggleTheme} style={buttonStyles}>
                    {isLightMode ? (
                        <Moon style={{ width: 18, height: 18, color: "#94a3b8" }} />
                    ) : (
                        <Sun style={{ width: 18, height: 18, color: "#94a3b8" }} />
                    )}
                </button>
            </div>
        </nav>
    )
}

export default Navigation
