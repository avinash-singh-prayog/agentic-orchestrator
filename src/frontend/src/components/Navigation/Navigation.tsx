/**
 * Navigation Component
 * 
 * Premium styled navigation with inline styles.
 */

import React, { useState, useEffect } from "react"
import { Sun, Moon, Activity, AlertCircle, Boxes, LogOut } from "lucide-react"
import { useTheme } from "@/contexts/ThemeContext"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import { useChatHistoryStore } from "@/stores/chatHistoryStore"

const Navigation: React.FC = () => {
    const { isLightMode, toggleTheme } = useTheme()
    const { getHealth } = useAgentAPI()
    const { logout } = useChatHistoryStore()
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
        background: isLightMode
            ? "rgba(255, 255, 255, 0.85)"
            : "linear-gradient(90deg, rgba(20, 22, 30, 0.98), rgba(26, 29, 40, 0.95))",
        borderBottom: isLightMode
            ? "1px solid rgba(0, 0, 0, 0.06)"
            : "1px solid rgba(255, 255, 255, 0.1)",
        backdropFilter: "blur(20px)",
        transition: "background 0.3s ease, border-color 0.3s ease",
    }

    const logoBoxStyles: React.CSSProperties = {
        width: 44,
        height: 44,
        borderRadius: 12,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #4f8fff, #9d7cf6)",
        boxShadow: isLightMode
            ? "0 4px 15px rgba(79, 143, 255, 0.25)"
            : "0 4px 15px rgba(79, 143, 255, 0.35)",
    }

    const healthBadgeStyles: React.CSSProperties = {
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 14px",
        borderRadius: 20,
        background: isLightMode ? "rgba(241, 245, 249, 0.8)" : "rgba(35, 39, 56, 0.8)",
        border: isLightMode ? "1px solid #e2e8f0" : "1px solid rgba(255, 255, 255, 0.12)",
    }

    const buttonStyles: React.CSSProperties = {
        width: 44,
        height: 44,
        borderRadius: 12,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: isLightMode ? "rgba(241, 245, 249, 0.8)" : "rgba(35, 39, 56, 0.6)",
        border: isLightMode ? "1px solid #e2e8f0" : "1px solid rgba(255, 255, 255, 0.12)",
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
                        background: "linear-gradient(135deg, #4f8fff, #c4b5fd)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                    }}>
                        Agentic Orchestrator
                    </span>
                    <span style={{ fontSize: 11, color: isLightMode ? "#64748b" : "#8b9cb8" }}>
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
                <button onClick={toggleTheme} style={buttonStyles} title={isLightMode ? "Switch to Dark Mode" : "Switch to Light Mode"}>
                    {isLightMode ? (
                        <Moon style={{ width: 18, height: 18, color: "#94a3b8" }} />
                    ) : (
                        <Sun style={{ width: 18, height: 18, color: "#94a3b8" }} />
                    )}
                </button>

                {/* Logout Button */}
                <button onClick={() => logout()} style={buttonStyles} title="Log Out">
                    <LogOut style={{ width: 18, height: 18, color: "#ef4444" }} />
                </button>
            </div>
        </nav>
    )
}

export default Navigation
