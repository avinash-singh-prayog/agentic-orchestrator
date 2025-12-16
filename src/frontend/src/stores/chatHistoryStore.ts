/**
 * Chat History Store - Hybrid Approach
 * 
 * Uses IndexedDB as cache for fast UI, syncs with backend API on page reload.
 * - Click on conversation: loads from IndexedDB cache (instant)
 * - Page reload: syncs with backend API (source of truth)
 */

import { create } from 'zustand'
import { API_ENDPOINTS } from '@/utils/const'
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
  tenantId: string | null
  userId: string | null
  conversations: Conversation[]
  activeConversationId: string | null
  messages: Message[]
  isLoading: boolean
  isLoadingMessages: boolean
  isSyncing: boolean
}

interface ChatHistoryActions {
  initSession: (tenantId: string, userId: string) => Promise<void>
  loadConversations: () => Promise<void>
  syncWithBackend: () => Promise<void>
  createNewConversation: () => Promise<string>
  setActiveConversation: (id: string | null) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  addUserMessage: (content: string) => Promise<void>
  addAssistantMessage: (content: string, activity?: { sender: string; receiver?: string; message: string; state?: string }[]) => Promise<void>
  getActiveThreadId: () => string | null
  reset: () => void
}

type ChatHistoryStore = ChatHistoryState & ChatHistoryActions

// ============================================================================
// Initial State
// ============================================================================

const initialState: ChatHistoryState = {
  tenantId: null,
  userId: null,
  conversations: [],
  activeConversationId: null,
  messages: [],
  isLoading: false,
  isLoadingMessages: false,
  isSyncing: false
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

  initSession: async (tenantId, userId) => {
    set({ tenantId, userId, isLoading: true })
    
    // Save session to IndexedDB
    await saveSession({ tenantId, userId, activeConversationId: null })
    
    // Load from IndexedDB first (fast)
    await get().loadConversations()
    
    // Restore last active conversation
    const session = await getSession()
    if (session?.activeConversationId) {
      await get().setActiveConversation(session.activeConversationId)
    }
    
    // Sync with backend in background
    get().syncWithBackend()
    
    set({ isLoading: false })
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
      
      // Remove conversations that don't exist in backend
      // FIXME: Disabled to prevent deleting local-only conversations before sync
      /*
      const backendIds = new Set(data.map(c => c.thread_id))
      const localConvs = await getDBConversations(tenantId, userId)
      for (const local of localConvs) {
        if (!backendIds.has(local.id)) {
          await deleteDBConversation(local.id)
        }
      }
      */
      
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
    await saveSession({ tenantId, userId, activeConversationId: threadId })
    
    return threadId
  },

  setActiveConversation: async (id) => {
    const { tenantId, userId, activeConversationId, conversations } = get()
    
    // If same conversation, don't reload
    if (id === activeConversationId) return
    
    set({ activeConversationId: id, isLoadingMessages: true })
    
    // Save to session
    if (tenantId && userId) {
      await saveSession({ tenantId, userId, activeConversationId: id })
    }
    
    if (id) {
      try {
        // Load from IndexedDB cache first (instant)
        const cachedMessages = await getDBMessages(id)
        
        // Check if this conversation exists in our local list
        const isLocalConversation = conversations.some(c => c.id === id)
        
        if (cachedMessages.length > 0) {
          // Use cache - has messages
          set({ messages: cachedMessages.map(convertDBMessage), isLoadingMessages: false })
        } else if (isLocalConversation) {
          // Local conversation with no messages (new/empty) - don't call API
          set({ messages: [], isLoadingMessages: false })
        } else if (tenantId && userId) {
          // Unknown conversation - fetch from API (synced from another device)
          const response = await fetch(
            `${API_URL}${API_ENDPOINTS.CONVERSATION(id)}?tenant_id=${tenantId}&user_id=${userId}`
          )
          
          if (response.ok) {
            const data: MessageInfo[] = await response.json()
            
            // Save to cache
            for (const msg of data) {
              await addDBMessage(id, msg.role, msg.content)
            }
            
            // Reload from cache
            const messages = await getDBMessages(id)
            set({ messages: messages.map(convertDBMessage) })
          } else {
            set({ messages: [] })
          }
        } else {
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

  reset: () => set(initialState)
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
  useChatHistoryStore(state => ({
    tenantId: state.tenantId,
    userId: state.userId
  }))

export const useIsLoadingHistory = () =>
  useChatHistoryStore(state => state.isLoading || state.isLoadingMessages)

export const useIsSyncing = () =>
  useChatHistoryStore(state => state.isSyncing)
