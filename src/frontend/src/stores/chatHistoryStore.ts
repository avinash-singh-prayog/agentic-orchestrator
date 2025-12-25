/**
 * Chat History Store - Hybrid Approach
 * 
 * Uses IndexedDB as cache for fast UI, syncs with backend API on page reload.
 * - Click on conversation: loads from IndexedDB cache (instant)
 * - Page reload: syncs with backend API (source of truth)
 */

import { create } from 'zustand'
import { useShallow } from 'zustand/react/shallow'
import { API_ENDPOINTS } from '@/utils/const'
import { type AgentActivityEvent } from '@/types/message'
import {
  type Conversation as DBConversation,
  type Message as DBMessage,
  db,
  getConversations as getDBConversations,
  getMessages as getDBMessages,
  createConversation as createDBConversation,
  addMessage as addDBMessage,
  updateConversation as updateDBConversation,
  deleteConversation as deleteDBConversation,
  getSession,
  saveSession
} from '@/utils/db'

const API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL || 'http://localhost:8000'

// ============================================================================
// Types
// ============================================================================

interface ConversationInfo {
  thread_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

interface MessageInfo {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  activity?: AgentActivityEvent[]
}

export interface LLMConfig {
  id?: string // Added ID
  provider: string
  model_name: string
  is_configured: boolean // helper
  is_active?: boolean
  config_name?: string
}

interface Conversation {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  messageCount: number
}

interface Message {
  id: string
  conversationId: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  activity?: { sender: string; receiver?: string; message: string; state?: string }[]
}

interface ChatHistoryState {
  isAuthenticated: boolean
  token: string | null // Access Token
  tenantId: string | null
  userId: string | null
  email: string | null
  name: string | null
  conversations: Conversation[]
  activeConversationId: string | null
  messages: Message[]
  isLoading: boolean
  isLoadingMessages: boolean
  isSyncing: boolean
  llmConfig: LLMConfig | null
  llmConfigs: LLMConfig[]
  activeLLMConfig: LLMConfig | null
  isSettingsOpen: boolean
}

interface ChatHistoryActions {
  initSession: () => Promise<void>
  login: (data: { userId: string; tenantId: string; email: string; name?: string; token: string }) => Promise<void>
  logout: () => Promise<void>
  loadConversations: () => Promise<void>
  syncWithBackend: () => Promise<void>
  createNewConversation: () => Promise<string>
  setActiveConversation: (id: string | null) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  addUserMessage: (content: string) => Promise<void>
  addAssistantMessage: (content: string, activity?: { sender: string; receiver?: string; message: string; state?: string }[]) => Promise<void>
  getActiveThreadId: () => string | null
  reset: () => void
  
  // Settings
  fetchLLMConfig: () => Promise<void>
  fetchConfigs: () => Promise<void>
  addConfig: (provider: string, modelName: string, apiKey: string, configName: string) => Promise<void>
  deleteConfig: (id: string) => Promise<void>
  activateConfig: (id: string) => Promise<void>
  
  updateLLMConfig: (provider: string, modelName: string, apiKey?: string) => Promise<void> // Legacy/Simple
  
  // UI Actions
  setSettingsOpen: (isOpen: boolean) => void
}

type ChatHistoryStore = ChatHistoryState & ChatHistoryActions

// ============================================================================
// Initial State
// ============================================================================

const initialState: ChatHistoryState = {
  isAuthenticated: false,
  token: null,
  tenantId: null,
  userId: null,
  email: null,
  name: null,
  conversations: [],
  activeConversationId: null,
  messages: [],
  isLoading: false,
  isLoadingMessages: false,
  isSyncing: false,
  llmConfig: null,
  llmConfigs: [],
  activeLLMConfig: null,
  isSettingsOpen: false
}

// ============================================================================
// Helpers
// ============================================================================

const convertDBConversation = (conv: DBConversation): Conversation => ({
  id: conv.id,
  title: conv.title,
  createdAt: new Date(conv.createdAt),
  updatedAt: new Date(conv.updatedAt),
  messageCount: conv.messageCount
})

const convertDBMessage = (msg: DBMessage): Message => ({
  id: msg.id,
  conversationId: msg.conversationId,
  role: msg.role,
  content: msg.content,
  timestamp: new Date(msg.timestamp),
  activity: msg.activity
})

// ============================================================================
// Store
// ============================================================================

export const useChatHistoryStore = create<ChatHistoryStore>((set, get) => ({
  ...initialState,

  initSession: async () => {
    set({ isLoading: true })
    
    try {
      // Restore session from IndexedDB
      const session = await getSession()
      if (session && session.userId && session.tenantId && session.token) {
        set({
          isAuthenticated: true,
          userId: session.userId,
          tenantId: session.tenantId,
          email: session.email || null,
          name: session.name || null,
          token: session.token
        })

        // Load conversations
        await get().loadConversations()
        
        // Restore active conversation
        if (session.activeConversationId) {
          await get().setActiveConversation(session.activeConversationId)
        }
        
        // Sync with backend
        get().syncWithBackend()
      }
    } catch (error) {
      console.error("Failed to init session:", error)
    } finally {
      set({ isLoading: false })
    }
  },

  login: async (data) => {
    set({ isLoading: true })
    
    const { userId, tenantId, email, name, token } = data
    
    // Save to IndexedDB
    await saveSession({ userId, tenantId, email, name, token, activeConversationId: null })
    
    set({
      isAuthenticated: true,
      token,
      userId,
      tenantId,
      email,
      name: name || null,
      isLoading: false
    })
    
    // Load data for this user
    await get().loadConversations()
    get().syncWithBackend()
  },

  logout: async () => {
    // Clear session from DB (but keep data? Or clear? Usually for security we clear session only)
    // To support multi-user on same device, we might want to keep data but just clear session.
    // For now, let's just clear session record.
    await saveSession({ userId: '', tenantId: '', email: '', name: '', activeConversationId: null }) // Or delete
    
    set(initialState)
  },

  loadConversations: async () => {
    const { tenantId, userId } = get()
    if (!tenantId || !userId) return
    
    try {
      // Load from IndexedDB cache
      const dbConversations = await getDBConversations(tenantId, userId)
      const conversations = dbConversations.map(convertDBConversation)
      set({ conversations })
    } catch (error) {
      console.error('Failed to load conversations from cache:', error)
    }
  },

  syncWithBackend: async () => {
    const { tenantId, userId } = get()
    if (!tenantId || !userId) return
    
    set({ isSyncing: true })
    
    try {
      const response = await fetch(
        `${API_URL}${API_ENDPOINTS.CONVERSATIONS}?tenant_id=${tenantId}&user_id=${userId}`
      )
      
      if (!response.ok) {
        console.error('Failed to sync conversations:', response.status)
        return
      }
      
      const data: ConversationInfo[] = await response.json()
      
      // Update IndexedDB with backend data
      for (const conv of data) {
        const existing = await db.conversations.get(conv.thread_id)
        if (existing) {
          // Update existing
          await updateDBConversation(conv.thread_id, {
            title: conv.title,
            messageCount: conv.message_count,
            updatedAt: new Date(conv.updated_at)
          })
        } else {
          // Add new
          await db.conversations.put({
            id: conv.thread_id,
            tenantId,
            userId,
            title: conv.title,
            createdAt: new Date(conv.created_at),
            updatedAt: new Date(conv.updated_at),
            messageCount: conv.message_count
          })
        }
      }
      
      // Reload from cache
      await get().loadConversations()
    } catch (error) {
      console.error('Failed to sync with backend:', error)
    } finally {
      set({ isSyncing: false })
    }
  },

  createNewConversation: async () => {
    const { tenantId, userId } = get()
    if (!tenantId || !userId) throw new Error('Session not initialized')
    
    const threadId = crypto.randomUUID()
    
    // Create in IndexedDB
    await createDBConversation(tenantId, userId, threadId, 'New Conversation')
    
    // Update state directly (don't use setActiveConversation to avoid API call)
    await get().loadConversations()
    
    // Set active with empty messages (new conversation has no messages)
    set({ activeConversationId: threadId, messages: [] })
    
    // Save to session
    await saveSession({ tenantId, userId, activeConversationId: threadId, email: get().email || undefined, name: get().name || undefined, token: get().token || undefined })
    
    return threadId
  },

  setActiveConversation: async (id) => {
    const { tenantId, userId, activeConversationId, conversations } = get()
    
    // If same conversation, don't reload
    if (id === activeConversationId) return
    
    set({ activeConversationId: id, isLoadingMessages: true })
    
    // Save to session
    if (tenantId && userId) {
      await saveSession({ tenantId, userId, activeConversationId: id, email: get().email || undefined, name: get().name || undefined, token: get().token || undefined })
    }
    
    if (id) {
      try {
        // Load from IndexedDB cache first (instant)
        const cachedMessages = await getDBMessages(id)
        
        // Get conversation info to check message_count
        const conv = conversations.find(c => c.id === id)
        const hasMessagesOnServer = conv && conv.messageCount > 0
        
        if (cachedMessages.length > 0) {
          // Use cache - has messages
          set({ messages: cachedMessages.map(convertDBMessage), isLoadingMessages: false })
        } else if (hasMessagesOnServer && tenantId && userId) {
          // Has messages on server but not in cache - fetch from API
          const response = await fetch(
            `${API_URL}${API_ENDPOINTS.CONVERSATION(id)}?tenant_id=${tenantId}&user_id=${userId}`
          )
          
          if (response.ok) {
            const data: MessageInfo[] = await response.json()
            
            // Save to cache
            for (const msg of data) {
              await addDBMessage(id, msg.role, msg.content, msg.activity)
            }
            
            // Reload from cache
            const messages = await getDBMessages(id)
            set({ messages: messages.map(convertDBMessage) })
          } else {
            console.error('Failed to fetch messages:', response.status)
            set({ messages: [] })
          }
        } else {
          // No messages on server (new conversation)
          set({ messages: [] })
        }
      } catch (error) {
        console.error('Failed to load messages:', error)
        set({ messages: [] })
      }
    } else {
      set({ messages: [] })
    }
    
    set({ isLoadingMessages: false })
  },

  deleteConversation: async (id) => {
    const { tenantId, userId, activeConversationId } = get()
    if (!tenantId || !userId) return
    
    try {
      // Delete from backend
      await fetch(
        `${API_URL}${API_ENDPOINTS.CONVERSATION(id)}?tenant_id=${tenantId}&user_id=${userId}`,
        { method: 'DELETE' }
      )
      
      // Delete from IndexedDB
      await deleteDBConversation(id)
      
      // Reload conversations
      await get().loadConversations()
      
      // Clear if was active
      if (activeConversationId === id) {
        set({ activeConversationId: null, messages: [] })
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  },

  addUserMessage: async (content) => {
    let { activeConversationId, tenantId, userId } = get()
    
    if (!activeConversationId) {
      if (!tenantId || !userId) throw new Error('Session not initialized')
      activeConversationId = await get().createNewConversation()
    }
    
    // Add to IndexedDB
    const dbMessage = await addDBMessage(activeConversationId!, 'user', content)
    
    // Update local state
    set(state => ({ 
      messages: [...state.messages, convertDBMessage(dbMessage)]
    }))
    
    // Reload conversations (updates title/count)
    await get().loadConversations()
  },

  addAssistantMessage: async (content, activity) => {
    const { activeConversationId } = get()
    console.log('[addAssistantMessage] Called with activity:', activity?.length, 'events, conversationId:', activeConversationId)
    if (!activeConversationId) return
    
    // Add to IndexedDB with activity
    const dbMessage = await addDBMessage(activeConversationId, 'assistant', content, activity)
    console.log('[addAssistantMessage] Saved to IndexedDB, message has activity:', !!dbMessage.activity, dbMessage.activity?.length)
    
    // Update local state
    set(state => ({ 
      messages: [...state.messages, convertDBMessage(dbMessage)]
    }))
    
    // Reload conversations in background
    get().loadConversations()
  },

  getActiveThreadId: () => get().activeConversationId,

  reset: () => set(initialState),

  fetchLLMConfig: async () => {
     // Legacy wrapper, calls fetchConfigs and sets active
     await get().fetchConfigs()
  },

  fetchConfigs: async () => {
    const { token } = get()
    if (!token) return
    
    try {
      const response = await fetch(`${API_URL}/supervisor-agent/settings/llm-configs`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const configs: LLMConfig[] = await response.json()
        const active = configs.find(c => c.is_active) || null
        set({ llmConfigs: configs, activeLLMConfig: active, llmConfig: active })
      }
    } catch (error) {
       console.error("Failed to fetch LLM configs", error)
    }
  },

  addConfig: async (provider, modelName, apiKey, configName) => {
      const { token } = get()
      if (!token) throw new Error("Not authenticated")
      
      const payload = {
          provider,
          model_name: modelName,
          api_key: apiKey,
          config_name: configName
      }
      
      const response = await fetch(`${API_URL}/supervisor-agent/settings/llm-configs`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })
      
      if (!response.ok) {
          throw new Error("Failed to add config")
      }
      
      await get().fetchConfigs()
  },
  
  activateConfig: async (id) => {
      const { token } = get()
      if (!token) return

      await fetch(`${API_URL}/supervisor-agent/settings/llm-configs/${id}/activate`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      await get().fetchConfigs()
  },
  
  deleteConfig: async (id) => {
      const { token } = get()
      if (!token) return

      await fetch(`${API_URL}/supervisor-agent/settings/llm-configs/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      await get().fetchConfigs()
  },
  
  updateLLMConfig: async (provider: string, modelName: string, apiKey?: string) => {
      const { token } = get()
      if (!token) throw new Error("Not authenticated")
      
      const payload = {
          provider,
          model_name: modelName,
          api_key: apiKey || "" // Send empty string if undefined, though backend handles it
      }
      
      const response = await fetch(`${API_URL}/supervisor-agent/settings/llm-config`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })
      
      if (!response.ok) {
          const err = await response.text()
          throw new Error(`Failed to update settings: ${err}`)
      }
      
      // Update local state immediately
      set({ 
          llmConfig: {
              provider,
              model_name: modelName,
              is_configured: !!apiKey || (get().llmConfig?.is_configured ?? false) // Approximate logic
          } 
      })
      // Refetch to be sure
      // get().fetchLLMConfig() 
  },

  setSettingsOpen: (isOpen) => set({ isSettingsOpen: isOpen })
}))

// ============================================================================
// Selector Hooks
// ============================================================================

export const useConversations = () => 
  useChatHistoryStore(state => state.conversations)

export const useActiveConversationId = () => 
  useChatHistoryStore(state => state.activeConversationId)

export const useChatMessages = () => 
  useChatHistoryStore(state => state.messages)

export const useChatSession = () => 
  useChatHistoryStore(useShallow(state => ({
    isAuthenticated: state.isAuthenticated,
    tenantId: state.tenantId,
    userId: state.userId,
    email: state.email,
    name: state.name
  })))

export const useIsLoadingHistory = () =>
  useChatHistoryStore(state => state.isLoading || state.isLoadingMessages)

export const useIsSyncing = () =>
  useChatHistoryStore(state => state.isSyncing)

