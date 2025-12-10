/**
 * Theme Context
 * 
 * Provides dark/light theme switching with localStorage persistence.
 */

import React, { createContext, useContext, useEffect, useState } from "react"

type Theme = "light" | "dark" | "system"

interface ThemeContextType {
    theme: Theme
    resolvedTheme: "light" | "dark"
    setTheme: (theme: Theme) => void
    toggleTheme: () => void
    isLightMode: boolean
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({
    children,
}) => {
    const [theme, setThemeState] = useState<Theme>(() => {
        if (typeof window !== "undefined") {
            const stored = localStorage.getItem("theme")
            if (stored === "light" || stored === "dark" || stored === "system") {
                return stored
            }
        }
        return "dark"
    })

    const [systemTheme, setSystemTheme] = useState<"light" | "dark">("dark")

    // Listen for system theme changes
    useEffect(() => {
        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
        setSystemTheme(mediaQuery.matches ? "dark" : "light")

        const handler = (e: MediaQueryListEvent) => {
            setSystemTheme(e.matches ? "dark" : "light")
        }

        mediaQuery.addEventListener("change", handler)
        return () => mediaQuery.removeEventListener("change", handler)
    }, [])

    const resolvedTheme = theme === "system" ? systemTheme : theme

    // Apply theme to document
    useEffect(() => {
        if (resolvedTheme === "light") {
            document.body.setAttribute("data-theme", "light")
        } else {
            document.body.removeAttribute("data-theme")
        }
        localStorage.setItem("theme", theme)
    }, [theme, resolvedTheme])

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme)
    }

    const toggleTheme = () => {
        setThemeState((prev) => (prev === "light" ? "dark" : "light"))
    }

    return (
        <ThemeContext.Provider
            value={{
                theme,
                resolvedTheme,
                setTheme,
                toggleTheme,
                isLightMode: resolvedTheme === "light",
            }}
        >
            {children}
        </ThemeContext.Provider>
    )
}

export const useTheme = (): ThemeContextType => {
    const context = useContext(ThemeContext)
    if (context === undefined) {
        throw new Error("useTheme must be used within a ThemeProvider")
    }
    return context
}
