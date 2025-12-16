/**
 * Chat Sidebar Component
 * 
 * Displays conversation history with navigation and new chat functionality.
 */

import React, { useEffect } from 'react'
import { Plus, MessageSquare, Trash2, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import {
    useChatHistoryStore,
    useConversations,
    useActiveConversationId,
    useIsLoadingHistory
} from '@/stores/chatHistoryStore'

interface ChatSidebarProps {
    isCollapsed?: boolean
    onToggleCollapse?: () => void
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
    isCollapsed = false,
    onToggleCollapse
}) => {
    const conversations = useConversations()
    const activeId = useActiveConversationId()
    const isLoading = useIsLoadingHistory()

    const {
        tenantId,
        userId,
        initSession,
        createNewConversation,
        setActiveConversation,
        deleteConversation
    } = useChatHistoryStore()

    // Initialize session on mount (use placeholder IDs for now)
    // In production, these would come from auth context
    useEffect(() => {
        if (!tenantId || !userId) {
            // TODO: Get from auth context
            const defaultTenantId = '507f1f77bcf86cd799439011' // Placeholder
            const defaultUserId = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' // Placeholder
            initSession(defaultTenantId, defaultUserId)
        }
    }, [tenantId, userId, initSession])

    const handleNewChat = async () => {
        await createNewConversation()
    }

    const handleSelectConversation = async (id: string) => {
        await setActiveConversation(id)
    }

    const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation()
        if (confirm('Delete this conversation?')) {
            await deleteConversation(id)
        }
    }

    const formatDate = (date: Date) => {
        const now = new Date()
        const diffMs = now.getTime() - new Date(date).getTime()
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

        if (diffDays === 0) return 'Today'
        if (diffDays === 1) return 'Yesterday'
        if (diffDays < 7) return `${diffDays} days ago`
        return new Date(date).toLocaleDateString()
    }

    // Collapsed state
    if (isCollapsed) {
        return (
            <div style={collapsedStyles}>
                <button onClick={onToggleCollapse} style={toggleButtonStyles}>
                    <ChevronRight style={{ width: 16, height: 16 }} />
                </button>
                <button onClick={handleNewChat} style={iconButtonStyles} title="New Chat">
                    <Plus style={{ width: 18, height: 18 }} />
                </button>
            </div>
        )
    }

    return (
        <div style={containerStyles}>
            {/* Header */}
            <div style={headerStyles}>
                <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9' }}>History</h3>
                <div style={{ display: 'flex', gap: 4 }}>
                    <button onClick={handleNewChat} style={newChatButtonStyles}>
                        <Plus style={{ width: 14, height: 14 }} />
                        New
                    </button>
                    {onToggleCollapse && (
                        <button onClick={onToggleCollapse} style={toggleButtonStyles}>
                            <ChevronLeft style={{ width: 14, height: 14 }} />
                        </button>
                    )}
                </div>
            </div>

            {/* Conversation List */}
            <div style={listStyles}>
                {isLoading ? (
                    <div style={emptyStateStyles}>
                        <Loader2 style={{ width: 20, height: 20, animation: 'spin 1s linear infinite' }} />
                    </div>
                ) : conversations.length === 0 ? (
                    <div style={emptyStateStyles}>
                        <MessageSquare style={{ width: 24, height: 24, opacity: 0.3, marginBottom: 8 }} />
                        <p style={{ fontSize: 12, color: '#64748b' }}>No conversations yet</p>
                    </div>
                ) : (
                    conversations.map(conv => (
                        <div
                            key={conv.id}
                            onClick={() => handleSelectConversation(conv.id)}
                            style={{
                                ...conversationItemStyles,
                                background: activeId === conv.id
                                    ? 'rgba(79, 143, 255, 0.15)'
                                    : 'transparent',
                                borderColor: activeId === conv.id
                                    ? 'rgba(79, 143, 255, 0.3)'
                                    : 'transparent'
                            }}
                        >
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <p style={titleStyles}>{conv.title}</p>
                                <p style={metaStyles}>
                                    {formatDate(conv.updatedAt)} · {conv.messageCount} messages
                                </p>
                            </div>
                            <button
                                onClick={(e) => handleDeleteConversation(e, conv.id)}
                                style={deleteButtonStyles}
                                title="Delete conversation"
                            >
                                <Trash2 style={{ width: 12, height: 12 }} />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}

// ============================================================================
// Styles
// ============================================================================

const containerStyles: React.CSSProperties = {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(15, 17, 23, 0.95)',
    borderRight: '1px solid rgba(255, 255, 255, 0.08)',
}

const collapsedStyles: React.CSSProperties = {
    width: 48,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 8,
    padding: '12px 0',
    background: 'rgba(15, 17, 23, 0.95)',
    borderRight: '1px solid rgba(255, 255, 255, 0.08)',
}

const headerStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 12px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
}

const newChatButtonStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '6px 10px',
    fontSize: 11,
    fontWeight: 500,
    color: '#6ba6ff',
    background: 'rgba(79, 143, 255, 0.1)',
    border: '1px solid rgba(79, 143, 255, 0.2)',
    borderRadius: 6,
    cursor: 'pointer',
}

const toggleButtonStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 28,
    height: 28,
    color: '#a8b5cf',
    background: 'transparent',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
}

const iconButtonStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 36,
    height: 36,
    color: '#6ba6ff',
    background: 'rgba(79, 143, 255, 0.1)',
    border: '1px solid rgba(79, 143, 255, 0.2)',
    borderRadius: 8,
    cursor: 'pointer',
}

const listStyles: React.CSSProperties = {
    flex: 1,
    overflow: 'auto',
    padding: 8,
}

const emptyStateStyles: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: 120,
    color: '#64748b',
}

const conversationItemStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid transparent',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    marginBottom: 4,
}

const titleStyles: React.CSSProperties = {
    fontSize: 12,
    fontWeight: 500,
    color: '#e2e8f0',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
}

const metaStyles: React.CSSProperties = {
    fontSize: 10,
    color: '#64748b',
    marginTop: 2,
}

const deleteButtonStyles: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 24,
    height: 24,
    color: '#64748b',
    background: 'transparent',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    opacity: 0.6,
    transition: 'opacity 0.15s ease',
}

export default ChatSidebar
