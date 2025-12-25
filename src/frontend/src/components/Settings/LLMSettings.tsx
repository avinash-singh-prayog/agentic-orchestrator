import React, { useState, useEffect } from 'react'
import { useChatHistoryStore } from '@/stores/chatHistoryStore'
import { X, Lock, Save, Loader2, CheckCircle, Server, Cpu, Trash2, Plus, ArrowLeft } from 'lucide-react'

interface LLMSettingsProps {
    isOpen: boolean
    onClose: () => void
}

export const LLMSettings: React.FC<LLMSettingsProps> = ({ isOpen, onClose }) => {
    const {
        llmConfigs,
        fetchConfigs,
        addConfig,
        deleteConfig,
        activateConfig,
        isLoading
    } = useChatHistoryStore()

    // UI State
    const [view, setView] = useState<'list' | 'add'>('list')

    // Form State
    const [configName, setConfigName] = useState('')
    const [provider, setProvider] = useState('openai')
    const [modelName, setModelName] = useState('')
    const [apiKey, setApiKey] = useState('')

    const [isSaving, setIsSaving] = useState(false)
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

    // Load data on open
    useEffect(() => {
        if (isOpen) {
            fetchConfigs()
            setView('list')
            setMessage(null)
            resetForm()
        }
    }, [isOpen, fetchConfigs])

    const resetForm = () => {
        setProvider('openai')
        setModelName('')
        setApiKey('')
        setConfigName('')
    }

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsSaving(true)
        setMessage(null)

        try {
            await addConfig(provider, modelName, apiKey, configName || `${provider} - ${modelName}`)
            setMessage({ type: 'success', text: 'Configuration added successfully' })
            resetForm()
            setView('list')
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to add configuration' })
        } finally {
            setIsSaving(false)
        }
    }

    const handleActivate = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation()
        try {
            await activateConfig(id)
        } catch (error) {
            console.error(error)
        }
    }

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation()
        if (confirm("Are you sure you want to delete this configuration?")) {
            await deleteConfig(id)
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="relative w-full max-w-md bg-[#1e293b] border border-slate-700 rounded-xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-700 bg-slate-800/50">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Server size={18} className="text-indigo-400" />
                        {view === 'list' ? 'LLM Configurations' : 'Add New Configuration'}
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white transition-colors p-1 hover:bg-slate-700 rounded-lg"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-0 overflow-y-auto custom-scrollbar flex-1 bg-slate-900/50">

                    {message && (
                        <div className={`mx-4 mt-4 p-3 rounded-lg text-sm flex items-center gap-2 ${message.type === 'success'
                            ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                            : 'bg-red-500/10 text-red-400 border border-red-500/20'
                            }`}>
                            {message.type === 'success' ? <CheckCircle size={16} /> : <Loader2 size={16} className="text-red-400" />}
                            {message.text}
                        </div>
                    )}

                    {view === 'list' ? (
                        <div className="p-4 space-y-3">
                            <p className="text-sm text-slate-400 mb-2">
                                Manage your AI models. Select one to activate it for the Supervisor Agent.
                            </p>

                            <div className="space-y-3 pb-20">
                                {llmConfigs.length === 0 && !isLoading && (
                                    <div className="text-center py-8 text-slate-500 text-sm border-2 border-dashed border-slate-800 rounded-xl">
                                        No configurations found.
                                    </div>
                                )}

                                {llmConfigs.map((config) => (
                                    <div
                                        key={config.id}
                                        onClick={(e) => config.id && handleActivate(config.id, e)}
                                        className={`group relative p-4 rounded-xl border transition-all cursor-pointer ${config.is_active
                                            ? 'bg-indigo-500/10 border-indigo-500/50 shadow-lg shadow-indigo-500/10'
                                            : 'bg-slate-800/50 border-slate-700 hover:border-slate-600 hover:bg-slate-800'
                                            }`}
                                    >
                                        <div className="flex items-start justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${config.is_active ? 'bg-indigo-500 text-white' : 'bg-slate-700 text-slate-400'
                                                    }`}>
                                                    <Cpu size={16} />
                                                </div>
                                                <div>
                                                    <h3 className={`text-sm font-medium ${config.is_active ? 'text-white' : 'text-slate-200'}`}>
                                                        {config.config_name || config.model_name}
                                                    </h3>
                                                    <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
                                                        {config.provider} • <span className="font-mono">{config.model_name}</span>
                                                    </p>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                {config.is_active && (
                                                    <span className="text-[10px] font-medium bg-indigo-500 text-white px-2 py-0.5 rounded-full flex items-center gap-1">
                                                        Active
                                                    </span>
                                                )}

                                                <button
                                                    onClick={(e) => config.id && handleDelete(config.id, e)}
                                                    className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                                                    title="Delete"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <form onSubmit={handleSave} className="p-4 space-y-5">
                            {/* Config Name */}
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Name (Optional)</label>
                                <input
                                    type="text"
                                    value={configName}
                                    onChange={(e) => setConfigName(e.target.value)}
                                    placeholder="My Custom GPT-4"
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 px-3 text-sm text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none placeholder:text-slate-600"
                                />
                            </div>

                            {/* Provider */}
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Provider</label>
                                <div className="relative">
                                    <select
                                        value={provider}
                                        onChange={(e) => setProvider(e.target.value)}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 px-3 text-sm text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none appearance-none"
                                    >
                                        <option value="openai">OpenAI</option>
                                        <option value="anthropic">Anthropic</option>
                                        <option value="groq">Groq</option>
                                        <option value="ollama">Ollama</option>
                                        <option value="openrouter">OpenRouter</option>
                                        <option value="gemini">Google Gemini</option>
                                    </select>
                                    <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
                                        <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            {/* Model Name */}
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Model Name</label>
                                <div className="relative group">
                                    <Cpu className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-indigo-400 transition-colors" size={16} />
                                    <input
                                        type="text"
                                        value={modelName}
                                        onChange={(e) => setModelName(e.target.value)}
                                        placeholder={provider === 'openai' ? 'gpt-4o' : 'llama3-70b-8192'}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 pl-9 pr-3 text-sm text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none placeholder:text-slate-600"
                                        required
                                    />
                                </div>
                            </div>

                            {/* API Key */}
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">API Key</label>
                                <div className="relative group">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-indigo-400 transition-colors" size={16} />
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder="sk-..."
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 pl-9 pr-3 text-sm text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none placeholder:text-slate-600"
                                        required
                                    />
                                </div>
                            </div>
                        </form>
                    )}
                </div>

                {/* Footer Actions */}
                <div className="p-4 bg-slate-800/50 border-t border-slate-700">
                    {view === 'list' ? (
                        <button
                            onClick={() => setView('add')}
                            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg shadow-indigo-500/20"
                        >
                            <Plus size={18} />
                            Add Configuration
                        </button>
                    ) : (
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setView('list')}
                                className="flex-1 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-slate-700 rounded-lg transition-colors border border-slate-700 hover:border-slate-600"
                            >
                                <ArrowLeft size={16} className="mr-2 inline" />
                                Back to List
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2 transition-transform active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {isSaving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
                                Save Config
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
