/**
 * Chat Area Component
 * 
 * Main chat interface with input, messages, and streaming display.
 */

import React, { useState, useRef, useEffect } from "react"
import { Send, Loader2 } from "lucide-react"
import { v4 as uuidv4 } from "uuid"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import { useStreamingActions, useStreamingStatus } from "@/stores/orchestratorStreamingStore"
import StreamingFeed from "./StreamingFeed"
import type { Message } from "@/types/message"
import { EXAMPLE_PROMPTS } from "@/utils/const"

interface ChatAreaProps {
    onProcessingChange?: (isProcessing: boolean) => void
}

const ChatArea: React.FC<ChatAreaProps> = ({ onProcessingChange }) => {
    const [input, setInput] = useState("")
    const [messages, setMessages] = useState<Message[]>([])
    const [useStreaming, setUseStreaming] = useState(true)
    const inputRef = useRef<HTMLInputElement>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const { sendMessage, loading: apiLoading } = useAgentAPI()
    const { startStreaming, reset } = useStreamingActions()
    const streamingStatus = useStreamingStatus()

    const isLoading = apiLoading || streamingStatus === "streaming" || streamingStatus === "connecting"

    // Notify parent about processing state
    useEffect(() => {
        onProcessingChange?.(isLoading)
    }, [isLoading, onProcessingChange])

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages])

    const handleSend = async () => {
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: uuidv4(),
            role: "user",
            content: input.trim(),
            timestamp: new Date(),
        }

        setMessages((prev) => [...prev, userMessage])
        const prompt = input.trim()
        setInput("")
        reset()

        if (useStreaming) {
            await startStreaming(prompt)
        } else {
            try {
                const response = await sendMessage(prompt)
                const assistantMessage: Message = {
                    id: uuidv4(),
                    role: "assistant",
                    content: response,
                    timestamp: new Date(),
                }
                setMessages((prev) => [...prev, assistantMessage])
            } catch (error) {
                const errorMessage: Message = {
                    id: uuidv4(),
                    role: "assistant",
                    content: "Sorry, an error occurred. Please try again.",
                    timestamp: new Date(),
                }
                setMessages((prev) => [...prev, errorMessage])
            }
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const handleExampleClick = (prompt: string) => {
        setInput(prompt)
        inputRef.current?.focus()
    }

    return (
        <div className="flex h-full flex-col bg-chat-background">
            {/* Messages area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Empty state with example prompts */}
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <h2 className="text-xl font-semibold text-node-text-primary mb-2">
                            Logistics Orchestrator
                        </h2>
                        <p className="text-sm text-node-text-secondary mb-6 max-w-md">
                            Ask me about shipping routes, rates, or booking shipments.
                            I'll coordinate with specialized agents to help you.
                        </p>

                        {/* Example prompts */}
                        <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                            {EXAMPLE_PROMPTS.map((prompt, index) => (
                                <button
                                    key={index}
                                    onClick={() => handleExampleClick(prompt)}
                                    className="px-3 py-2 text-xs text-node-text-secondary bg-node-background border border-border-color rounded-lg hover:bg-node-background-hover hover:text-node-text-primary transition-colors"
                                >
                                    {prompt}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Message history */}
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                        <div
                            className={`max-w-[80%] rounded-lg px-4 py-3 ${message.role === "user"
                                    ? "bg-accent-primary text-white"
                                    : "bg-node-background text-chat-text border border-border-color"
                                }`}
                        >
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        </div>
                    </div>
                ))}

                {/* Streaming feed */}
                {useStreaming && <StreamingFeed />}

                <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="border-t border-border-color bg-chat-background p-4">
                <div className="flex items-center gap-3">
                    {/* Streaming toggle */}
                    <button
                        onClick={() => setUseStreaming(!useStreaming)}
                        className={`px-3 py-2 text-xs rounded-lg border transition-colors ${useStreaming
                                ? "bg-accent-primary/20 border-accent-primary text-accent-primary"
                                : "bg-node-background border-border-color text-node-text-secondary"
                            }`}
                        title={useStreaming ? "Streaming enabled" : "Streaming disabled"}
                    >
                        {useStreaming ? "Stream" : "Sync"}
                    </button>

                    {/* Input field */}
                    <div className="flex-1 relative">
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Ask about shipping routes, rates, or bookings..."
                            className="w-full rounded-lg border border-border-color bg-chat-input-background px-4 py-3 pr-12 text-sm text-chat-text placeholder-node-text-secondary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                            disabled={isLoading}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            className="absolute right-2 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-lg bg-accent-primary text-white transition-colors hover:bg-accent-primary/80 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ChatArea
