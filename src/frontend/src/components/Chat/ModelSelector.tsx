import React, { useState, useEffect, useRef } from 'react'
import { useChatHistoryStore } from '@/stores/chatHistoryStore'
import { Cpu, ChevronDown, Check, Plus } from 'lucide-react'

export const ModelSelector: React.FC = () => {
    const {
        llmConfigs,
        activeLLMConfig,
        activateConfig,
        fetchConfigs,
        setSettingsOpen
    } = useChatHistoryStore()

    const [isOpen, setIsOpen] = useState(false)
    const dropdownRef = useRef<HTMLDivElement>(null)

    // Close dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    // Fetch configs on load if not loaded
    useEffect(() => {
        if (llmConfigs.length === 0) {
            fetchConfigs()
        }
    }, [])

    const handleSelect = async (id: string) => {
        await activateConfig(id)
        setIsOpen(false)
    }

    const handleOpenSettings = () => {
        setSettingsOpen(true)
        setIsOpen(false)
    }

    const buttonStyles: React.CSSProperties = {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 12px',
        borderRadius: 8,
        background: 'rgba(255, 255, 255, 0.05)',
        border: '1px solid var(--border-subtle)',
        color: 'var(--text-secondary)',
        fontSize: 12,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        minWidth: 140,
        justifyContent: 'space-between'
    }

    const dropdownStyles: React.CSSProperties = {
        position: 'absolute',
        top: '100%',
        right: 0,
        marginTop: 8,
        width: 240,
        background: 'var(--bg-card)',
        border: '1px solid var(--border-light)',
        borderRadius: 12,
        boxShadow: 'var(--shadow-lg)',
        overflow: 'hidden',
        zIndex: 50,
        padding: 4
    }

    const itemStyles = (isActive: boolean): React.CSSProperties => ({
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        borderRadius: 8,
        background: isActive ? 'var(--accent-primary-bg)' : 'transparent',
        border: 'none',
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'background 0.2s',
        marginBottom: 2
    })

    return (
        <div style={{ position: 'relative', zIndex: 20 }} ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={buttonStyles}
                className="hover:bg-white/10 hover:border-white/20 hover:text-white"
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                    <Cpu size={14} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                    <span style={{ fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 100 }}>
                        {activeLLMConfig ? (activeLLMConfig.config_name || activeLLMConfig.model_name) : 'Select Model'}
                    </span>
                </div>
                <ChevronDown size={12} style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }} />
            </button>

            {isOpen && (
                <div style={dropdownStyles}>
                    <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-subtle)', marginBottom: 4 }}>
                        <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Select Model
                        </span>
                    </div>

                    <div style={{ maxHeight: 240, overflowY: 'auto' }} className="custom-scrollbar">
                        {llmConfigs.length > 0 ? (
                            llmConfigs.map((config) => (
                                <button
                                    key={config.id}
                                    onClick={() => config.id && handleSelect(config.id)}
                                    style={itemStyles(!!config.is_active)}
                                    className="hover:bg-white/5"
                                >
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, overflow: 'hidden' }}>
                                        <span style={{ fontSize: 13, fontWeight: 500, color: config.is_active ? 'var(--accent-primary)' : 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {config.config_name || config.model_name}
                                        </span>
                                        <span style={{ fontSize: 11, color: 'var(--text-tertiary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {config.provider} • {config.model_name}
                                        </span>
                                    </div>
                                    {config.is_active && <Check size={14} style={{ color: 'var(--accent-primary)', flexShrink: 0, marginLeft: 8 }} />}
                                </button>
                            ))
                        ) : (
                            <div style={{ padding: '12px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>
                                No configurations found
                            </div>
                        )}
                    </div>

                    <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: 4, paddingTop: 4 }}>
                        <button
                            onClick={handleOpenSettings}
                            style={{ ...itemStyles(false), justifyContent: 'flex-start', gap: 8, color: 'var(--text-secondary)' }}
                            className="hover:bg-white/5 hover:text-white"
                        >
                            <Plus size={14} />
                            <span style={{ fontSize: 12, fontWeight: 500 }}>Add New Configuration</span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

