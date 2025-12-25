/**
 * IndexedDB Database Configuration
 * 
 * Uses Dexie.js for type-safe IndexedDB access.
 * Stores conversation metadata, messages, and agent activity for offline access.
 */

import Dexie, { type Table } from 'dexie'

// ============================================================================
// Types
// ============================================================================

export interface Conversation {
  id: string              // thread_id from backend
  tenantId: string        // Tenant ObjectId
  userId: string          // User UUID
  title: string           // Auto-generated from first message
  createdAt: Date
  updatedAt: Date
  messageCount: number
}

export interface AgentActivityEvent {
  sender: string
  receiver?: string
  message: string
  state?: string
}

export interface Message {
  id: string
  conversationId: string  // Maps to Conversation.id (thread_id)
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  activity?: AgentActivityEvent[]  // Agent activity for assistant messages
}

export interface UserSession {
  id: string              // 'current' - singleton
  tenantId: string
  userId: string
  email?: string
  name?: string
  token?: string
  activeConversationId: string | null
}

// ============================================================================
// Database Schema
// ============================================================================

class ChatDatabase extends Dexie {
  conversations!: Table<Conversation>
  messages!: Table<Message>
  sessions!: Table<UserSession>

  constructor() {
    super('orchestrator-chat')
    
    // Version 2: Added activity field to messages
    this.version(2).stores({
      // Indexed fields for fast queries
      conversations: 'id, tenantId, userId, [tenantId+userId], updatedAt',
      messages: 'id, conversationId, timestamp',
      sessions: 'id'
    })
    
    // Keep v1 for migration path
    this.version(1).stores({
      conversations: 'id, tenantId, userId, [tenantId+userId], updatedAt',
      messages: 'id, conversationId, timestamp',
      sessions: 'id'
    })
  }
}

export const db = new ChatDatabase()

// ============================================================================
// Database Operations
// ============================================================================

/**
 * Create a new conversation
 */
export async function createConversation(
  tenantId: string,
  userId: string,
  threadId: string,
  title: string = 'New Conversation'
): Promise<Conversation> {
  const conversation: Conversation = {
    id: threadId,
    tenantId,
    userId,
    title,
    createdAt: new Date(),
    updatedAt: new Date(),
    messageCount: 0
  }
  
  await db.conversations.add(conversation)
  return conversation
}

/**
 * Get all conversations for a tenant/user
 */
export async function getConversations(
  tenantId: string,
  userId: string
): Promise<Conversation[]> {
  return db.conversations
    .where('[tenantId+userId]')
    .equals([tenantId, userId])
    .reverse()
    .sortBy('updatedAt')
}

/**
 * Get a single conversation by ID
 */
export async function getConversation(id: string): Promise<Conversation | undefined> {
  return db.conversations.get(id)
}

/**
 * Update conversation (title, updatedAt, messageCount)
 */
export async function updateConversation(
  id: string,
  updates: Partial<Pick<Conversation, 'title' | 'updatedAt' | 'messageCount'>>
): Promise<void> {
  await db.conversations.update(id, updates)
}

/**
 * Delete a conversation and its messages
 */
export async function deleteConversation(id: string): Promise<void> {
  await db.transaction('rw', [db.conversations, db.messages], async () => {
    await db.messages.where('conversationId').equals(id).delete()
    await db.conversations.delete(id)
  })
}

/**
 * Add a message to a conversation
 */
export async function addMessage(
  conversationId: string,
  role: 'user' | 'assistant',
  content: string,
  activity?: AgentActivityEvent[]
): Promise<Message> {
  const message: Message = {
    id: crypto.randomUUID(),
    conversationId,
    role,
    content,
    timestamp: new Date(),
    ...(activity && activity.length > 0 ? { activity } : {})
  }
  
  await db.transaction('rw', [db.messages, db.conversations], async () => {
    await db.messages.add(message)
    
    // Update conversation metadata
    const conversation = await db.conversations.get(conversationId)
    if (conversation) {
      const updates: Partial<Conversation> = {
        updatedAt: new Date(),
        messageCount: (conversation.messageCount || 0) + 1
      }
      
      // Auto-generate title from first user message
      if (role === 'user' && conversation.messageCount === 0) {
        updates.title = content.slice(0, 50) + (content.length > 50 ? '...' : '')
      }
      
      await db.conversations.update(conversationId, updates)
    }
  })
  
  return message
}

/**
 * Get all messages for a conversation
 */
export async function getMessages(conversationId: string): Promise<Message[]> {
  return db.messages
    .where('conversationId')
    .equals(conversationId)
    .sortBy('timestamp')
}

/**
 * Get or create user session
 */
export async function getSession(): Promise<UserSession | undefined> {
  return db.sessions.get('current')
}

/**
 * Save user session
 */
export async function saveSession(session: Omit<UserSession, 'id'>): Promise<void> {
  await db.sessions.put({ id: 'current', ...session })
}

/**
 * Clear all data (for logout)
 */
export async function clearAllData(): Promise<void> {
  await db.transaction('rw', [db.conversations, db.messages, db.sessions], async () => {
    await db.conversations.clear()
    await db.messages.clear()
    await db.sessions.clear()
  })
}
