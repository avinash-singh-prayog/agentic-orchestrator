import React, { useState, useEffect } from 'react'
import { useChatHistoryStore } from '@/stores/chatHistoryStore'
import { API_ENDPOINTS } from '@/utils/const'
import axios from 'axios'
import { Loader2, Mail, Lock, User, ArrowRight, CheckCircle, AlertCircle } from 'lucide-react'

const API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL
if (!API_URL) {
    throw new Error('VITE_ORCHESTRATOR_API_URL is not defined')
}

type AuthView = 'login' | 'register' | 'forgot-password' | 'reset-password'

const AuthScreen: React.FC = () => {
    const login = useChatHistoryStore(state => state.login)

    const [view, setView] = useState<AuthView>('login')
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [successMessage, setSuccessMessage] = useState<string | null>(null)

    // Form State
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [name, setName] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [resetToken, setResetToken] = useState<string | null>(null)

    // Check for reset token on mount
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const token = params.get('token')
        if (token) {
            setResetToken(token)
            setView('reset-password')
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname)
        }
    }, [])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)
        setError(null)
        setSuccessMessage(null)

        try {
            if (view === 'login') {
                const response = await axios.post(`${API_URL}${API_ENDPOINTS.AUTH.LOGIN}`, {
                    email,
                    password
                })

                const { user } = response.data

                // Update local session
                await login({
                    userId: user.id,
                    tenantId: user.tenant_id,
                    email: user.email,
                    name: user.name,
                    token: response.data.access_token
                })

            } else if (view === 'register') {
                const response = await axios.post(`${API_URL}${API_ENDPOINTS.AUTH.REGISTER}`, {
                    email,
                    password,
                    name: name || undefined
                })

                const { user } = response.data

                await login({
                    userId: user.id,
                    tenantId: user.tenant_id,
                    email: user.email,
                    name: user.name,
                    token: response.data.access_token
                })

            } else if (view === 'forgot-password') {
                await axios.post(`${API_URL}${API_ENDPOINTS.AUTH.FORGOT_PASSWORD}`, {
                    email
                })
                setSuccessMessage('If an account exists, a reset link has been sent.')

            } else if (view === 'reset-password') {
                if (password !== confirmPassword) {
                    throw new Error("Passwords do not match")
                }

                if (!resetToken) {
                    throw new Error("Missing reset token")
                }

                await axios.post(`${API_URL}${API_ENDPOINTS.AUTH.RESET_PASSWORD}`, {
                    token: resetToken,
                    new_password: password
                })

                setSuccessMessage('Password reset successfully. Please login.')
                setTimeout(() => setView('login'), 2000)
            }
        } catch (err: any) {
            console.error("Auth error:", err)
            const msg = err.response?.data?.detail
                ? (typeof err.response.data.detail === 'string' ? err.response.data.detail : err.response.data.detail.message)
                : err.message || "An error occurred"
            setError(msg)
        } finally {
            setIsLoading(false)
        }
    }

    const switchView = (newView: AuthView) => {
        setView(newView)
        setError(null)
        setSuccessMessage(null)
        setPassword('')
        setConfirmPassword('')
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen w-full bg-[var(--bg-app)] text-[var(--text-primary)] p-4 relative overflow-hidden transition-colors duration-300">

            {/* Background Elements */}
            <div
                className="absolute inset-0 pointer-events-none"
                style={{
                    backgroundImage: 'radial-gradient(var(--color-grid) 1px, transparent 1px)',
                    backgroundSize: '30px 30px'
                }}
            />

            {/* Glow Orbs */}
            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[var(--accent-primary)]/10 rounded-full blur-3xl pointer-events-none mix-blend-screen" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none mix-blend-screen" />

            {/* Main Card */}
            <div className="w-full max-w-md bg-[var(--bg-panel)] border border-[var(--border-subtle)] rounded-2xl shadow-xl p-8 relative z-10 backdrop-blur-xl transition-colors duration-300">

                {/* Header */}
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-[var(--accent-primary)] to-purple-500 mb-2">
                        Prayog Orchestrator
                    </h1>
                    <p className="text-[var(--text-tertiary)] text-sm">
                        {view === 'login' && "Welcome back! Login to continue."}
                        {view === 'register' && "Create an account to get started."}
                        {view === 'forgot-password' && "Reset your password."}
                        {view === 'reset-password' && "Set a new password."}
                    </p>
                </div>

                {/* Error / Success Messages */}
                {error && (
                    <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-500 text-sm">
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}

                {successMessage && (
                    <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-3 text-green-500 text-sm">
                        <CheckCircle size={18} />
                        <span>{successMessage}</span>
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-5">

                    {view === 'register' && (
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Full Name</label>
                            <div className="relative group">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] group-focus-within:text-[var(--text-accent)] transition-colors" size={18} />
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="w-full bg-[var(--bg-app)] border border-[var(--border-light)] rounded-lg py-3 pl-10 pr-4 outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)] transition-all text-sm text-[var(--text-primary)]"
                                    placeholder="John Doe"
                                    required
                                />
                            </div>
                        </div>
                    )}

                    {(view === 'login' || view === 'register' || view === 'forgot-password') && (
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Email Address</label>
                            <div className="relative group">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] group-focus-within:text-[var(--text-accent)] transition-colors" size={18} />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full bg-[var(--bg-app)] border border-[var(--border-light)] rounded-lg py-3 pl-10 pr-4 outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)] transition-all text-sm text-[var(--text-primary)]"
                                    placeholder="name@company.com"
                                    required
                                />
                            </div>
                        </div>
                    )}

                    {(view === 'login' || view === 'register' || view === 'reset-password') && (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                                    {view === 'reset-password' ? 'New Password' : 'Password'}
                                </label>
                                {view === 'login' && (
                                    <button
                                        type="button"
                                        onClick={() => switchView('forgot-password')}
                                        className="text-xs text-[var(--text-accent)] hover:opacity-80 transition-opacity"
                                    >
                                        Forgot Password?
                                    </button>
                                )}
                            </div>
                            <div className="relative group">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] group-focus-within:text-[var(--text-accent)] transition-colors" size={18} />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full bg-[var(--bg-app)] border border-[var(--border-light)] rounded-lg py-3 pl-10 pr-4 outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)] transition-all text-sm text-[var(--text-primary)]"
                                    placeholder="••••••••"
                                    required
                                    minLength={6}
                                />
                            </div>
                        </div>
                    )}

                    {view === 'reset-password' && (
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">Confirm Password</label>
                            <div className="relative group">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] group-focus-within:text-[var(--text-accent)] transition-colors" size={18} />
                                <input
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="w-full bg-[var(--bg-app)] border border-[var(--border-light)] rounded-lg py-3 pl-10 pr-4 outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)] transition-all text-sm text-[var(--text-primary)]"
                                    placeholder="••••••••"
                                    required
                                    minLength={6}
                                />
                            </div>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-all transform active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed mt-4 shadow-lg shadow-indigo-500/20"
                    >
                        {isLoading ? (
                            <Loader2 className="animate-spin" size={18} />
                        ) : (
                            <>
                                {view === 'login' && <span>Sign In</span>}
                                {view === 'register' && <span>Create Account</span>}
                                {view === 'forgot-password' && <span>Send Reset Link</span>}
                                {view === 'reset-password' && <span>Reset Password</span>}
                                <ArrowRight size={16} />
                            </>
                        )}
                    </button>
                </form>

                {/* Footer */}
                <div className="mt-8 text-center text-sm text-[var(--text-tertiary)]">
                    {view === 'login' && (
                        <p>
                            Don't have an account?{' '}
                            <button
                                onClick={() => switchView('register')}
                                className="text-[var(--text-accent)] hover:opacity-80 font-medium transition-opacity"
                            >
                                Sign up
                            </button>
                        </p>
                    )}

                    {(view === 'register' || view === 'forgot-password' || view === 'reset-password') && (
                        <p>
                            Already have an account?{' '}
                            <button
                                onClick={() => switchView('login')}
                                className="text-[var(--text-accent)] hover:opacity-80 font-medium transition-opacity"
                            >
                                Sign in
                            </button>
                        </p>
                    )}
                </div>
            </div>

            {/* Disclaimer */}
            <div className="mt-8 text-[var(--text-tertiary)] text-xs opacity-50">
                &copy; 2024 Prayog Agentic Orchestrator. All rights reserved.
            </div>
        </div>
    )
}

export default AuthScreen
