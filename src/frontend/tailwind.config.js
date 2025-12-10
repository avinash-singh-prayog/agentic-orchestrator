export default {
    darkMode: ["class"],
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {
            colors: {
                "app-background": "var(--app-background)",
                "node-background": "var(--node-background)",
                "node-background-hover": "var(--node-background-hover)",
                "node-background-active": "var(--node-background-active)",
                "node-text-primary": "var(--node-text-primary)",
                "node-text-secondary": "var(--node-text-secondary)",
                "accent-primary": "var(--accent-primary)",
                "chat-background": "var(--chat-background)",
                "chat-text": "var(--chat-text)",
                "chat-input-background": "var(--chat-input-background)",
                "sidebar-background": "var(--sidebar-background)",
                "nav-background": "var(--nav-background)",
                "nav-border": "var(--nav-border)",
                "border-color": "var(--border-color)",
                "transport-background": "var(--transport-background)",
                "success": "var(--success)",
                "warning": "var(--warning)",
                "error": "var(--error)",
            },
            fontFamily: {
                inter: ["Inter", "system-ui", "sans-serif"],
            },
            animation: {
                fadeInDropdown: "fadeInDropdown 0.3s ease-out",
                scaleIn: "scaleIn 0.25s ease-in-out",
                pulse: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                "edge-flow": "edgeFlow 2s linear infinite",
            },
            keyframes: {
                fadeInDropdown: {
                    "0%": { opacity: "0", transform: "translateY(-10px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                scaleIn: {
                    "0%": { transform: "scale(0.95)", opacity: "0" },
                    "100%": { transform: "scale(1)", opacity: "1" },
                },
                edgeFlow: {
                    "0%": { strokeDashoffset: "24" },
                    "100%": { strokeDashoffset: "0" },
                },
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
}
