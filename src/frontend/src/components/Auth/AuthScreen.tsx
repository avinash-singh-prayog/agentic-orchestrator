import React, { useState, useEffect } from 'react';
import { useChatHistoryStore } from '@/stores/chatHistoryStore';
import { Loader2, Eye, EyeOff, ArrowLeft } from 'lucide-react';

const API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL || 'http://localhost:9004';

type AuthView = 'login' | 'register' | 'forgot-password' | 'reset-password';

const AuthScreen: React.FC = () => {
    const [view, setView] = useState<AuthView>('login');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [token, setToken] = useState<string | null>(null);
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const loginAction = useChatHistoryStore(state => state.login);

    useEffect(() => {
        // Check for reset token in URL
        const params = new URLSearchParams(window.location.search);
        const resetToken = params.get('token');
        if (resetToken) {
            setToken(resetToken);
            setView('reset-password');
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccessMessage(null);
        setLoading(true);

        try {
            let endpoint = '';
            let body = {};

            if (view === 'login') {
                endpoint = '/supervisor-agent/auth/login';
                body = { email, password };
            } else if (view === 'register') {
                endpoint = '/supervisor-agent/auth/register';
                body = { email, password, name };
            } else if (view === 'forgot-password') {
                endpoint = '/supervisor-agent/auth/forgot-password';
                body = { email };
            } else if (view === 'reset-password') {
                endpoint = '/supervisor-agent/auth/reset-password';
                body = { token, new_password: password };
            }

            const response = await fetch(`${API_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Authentication failed');
            }

            // Handle success based on view
            if (view === 'login' || view === 'register') {
                await loginAction({
                    userId: data.user.id,
                    tenantId: data.user.tenant_id,
                    email: data.user.email,
                    name: data.user.name
                });
            } else if (view === 'forgot-password') {
                setSuccessMessage(data.message || "Reset link sent!");
            } else if (view === 'reset-password') {
                setSuccessMessage("Password reset successfully. Please login.");
                setTimeout(() => setView('login'), 2000);
            }

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    const getTitle = () => {
        switch (view) {
            case 'login': return 'Welcome Back';
            case 'register': return 'Create Account';
            case 'forgot-password': return 'Reset Password';
            case 'reset-password': return 'New Password';
        }
    };

    const getSubtitle = () => {
        switch (view) {
            case 'login': return 'Sign in to access your agent workspace';
            case 'register': return 'Get started with your intelligent orchestrator';
            case 'forgot-password': return 'Enter your email to receive a reset link';
            case 'reset-password': return 'Enter your new password below';
        }
    };

    const getButtonText = () => {
        if (loading) return <Loader2 className="animate-spin h-6 w-6" />;
        switch (view) {
            case 'login': return 'Sign In';
            case 'register': return 'Create Account';
            case 'forgot-password': return 'Send Reset Link';
            case 'reset-password': return 'Reset Password';
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)] relative overflow-hidden">
            {/* Background Ambience */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none" />
            <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 blur-[120px] rounded-full pointer-events-none" />

            <div className="w-full max-w-lg p-12 glass rounded-3xl shadow-2xl relative z-10 animate-fade-in-up border border-white/10" style={{ padding: '3rem' }}>
                <div className="text-center mb-10">
                    <h1 className="text-4xl font-bold mb-3 text-white tracking-tight">
                        {getTitle()}
                    </h1>
                    <p className="text-[var(--text-secondary)] text-base font-light">
                        {getSubtitle()}
                    </p>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 text-red-200 rounded-xl text-sm flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-red-400 shrink-0" />
                        <span className="font-medium">{error}</span>
                    </div>
                )}

                {successMessage && (
                    <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 text-green-200 rounded-xl text-sm flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-green-400 shrink-0" />
                        <span className="font-medium">{successMessage}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="flex flex-col px-4" style={{ gap: '1.5rem' }}>
                    {/* Name Field (Register only) */}
                    {view === 'register' && (
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-[var(--text-secondary)] ml-1">Name</label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full input-modern h-12 text-lg placeholder:text-slate-500"
                                style={{ paddingLeft: '1rem' }}
                                placeholder="John Doe"
                                required
                            />
                        </div>
                    )}

                    {/* Email Field (All except Reset Password - unless we want to confirm email) */}
                    {view !== 'reset-password' && (
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-[var(--text-secondary)] ml-1">Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full input-modern h-12 text-lg placeholder:text-slate-500"
                                style={{ paddingLeft: '1rem' }}
                                placeholder="name@company.com"
                                required
                            />
                        </div>
                    )}

                    {/* Password Field (Login, Register, Reset Password) */}
                    {view !== 'forgot-password' && (
                        <div className="space-y-2">
                            <div className="flex justify-between items-center ml-1">
                                <label className="block text-sm font-medium text-[var(--text-secondary)]">
                                    {view === 'reset-password' ? 'New Password' : 'Password'}
                                </label>
                                {view === 'login' && (
                                    <button
                                        type="button"
                                        onClick={() => setView('forgot-password')}
                                        className="text-xs text-[var(--accent-primary)] hover:text-white transition-colors"
                                    >
                                        Forgot Password?
                                    </button>
                                )}
                            </div>
                            <div className="relative">
                                <input
                                    type={showPassword ? "text" : "password"}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full input-modern h-12 text-lg placeholder:text-slate-500 pr-10"
                                    style={{ paddingLeft: '1rem' }}
                                    placeholder="••••••••"
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-white transition-colors"
                                >
                                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                </button>
                            </div>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full h-12 bg-gradient-to-r from-[#4f8fff] to-[#8b5cf6] hover:from-[#3b7cf6] hover:to-[#7c3aed] text-white text-lg font-semibold rounded-xl transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center hover-lift mt-2 active:scale-95 duration-200"
                    >
                        {getButtonText()}
                    </button>

                    {/* Back to Login for Forgot Password */}
                    {view === 'forgot-password' && (
                        <button
                            type="button"
                            onClick={() => setView('login')}
                            className="w-full flex items-center justify-center gap-2 text-[var(--text-secondary)] hover:text-white transition-colors mt-2"
                        >
                            <ArrowLeft size={16} />
                            Back to Login
                        </button>
                    )}
                </form>

                {(view === 'login' || view === 'register') && (
                    <div className="mt-10 text-center pt-6 border-t border-white/5 px-4">
                        <p className="text-sm text-[var(--text-secondary)]">
                            {view === 'login' ? "Don't have an account? " : "Already have an account? "}
                            <button
                                onClick={() => setView(view === 'login' ? 'register' : 'login')}
                                className="text-[#4f8fff] hover:text-[#8b5cf6] font-semibold transition-colors ml-1"
                            >
                                {view === 'login' ? 'Sign Up' : 'Log In'}
                            </button>
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AuthScreen;
