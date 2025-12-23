"""
Supervisor Agent API.

Entry point for the supervisor agent with factory initialization.
Multi-tenant chat context persistence via PostgreSQL checkpointer.
"""

import json
import uuid
from typing import AsyncGenerator, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, APIRouter
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from agntcy_app_sdk.factory import AgntcyFactory
from agent.shared import set_factory
from agent.graph import build_graph
from agent.memory import get_checkpointer

# Try to import observability
try:
    from ioa_observe.sdk.tracing import session_start
    HAS_OBSERVABILITY = True
except ImportError:
    def session_start():
        pass
    HAS_OBSERVABILITY = False


from app.auth import (
    ensure_users_table, 
    UserRegisterRequest, 
    UserLoginRequest, 
    UserForgotPasswordRequest,
    UserResetPasswordRequest,
    TokenResponse, 
    create_user, 
    authenticate_user, 
    create_password_reset_token,
    reset_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    # Database error classes
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTimeoutError
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan for startup/shutdown."""
    # Startup
    set_factory(AgntcyFactory("orchestrator.supervisor_agent", enable_tracing=False))
    try:
        import asyncio
        from agent.memory import checkpointer_lifespan
        
        # Initialize checkpointer context
        async with checkpointer_lifespan():
            # Run other init tasks
            await asyncio.wait_for(ensure_users_table(), timeout=5.0)
            yield
    except Exception as e:
        print(f"CRITICAL: Application startup failed: {e}")
        # Yielding here allows the app to start even if init fails (for health checks),
        # but checkpointer will be None, causing fallback behavior.
        yield
    # Shutdown (cleanup if needed)


app = FastAPI(title="Supervisor Agent", lifespan=lifespan)
router = APIRouter(prefix="/supervisor-agent")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Build base graph (checkpointer added at runtime)
graph = build_graph()


# ============================================================================
# Auth Endpoints
# ============================================================================

@router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegisterRequest):
    """Register a new user with comprehensive error handling."""
    try:
        user = await create_user(user_data)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id, "tenant_id": user.tenant_id},
            expires_delta=None
        )
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "database_connection_error",
                "message": "Unable to connect to database. Please try again later.",
                "details": str(e.message)
            }
        )
    except DatabaseTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "database_timeout",
                "message": "Database operation timed out. Please try again.",
                "details": str(e.message)
            }
        )
    except DatabaseQueryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_query_error",
                "message": "A database error occurred during registration.",
                "details": str(e.message)
            }
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "An unexpected database error occurred.",
                "details": str(e.message)
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Registration failed due to an unexpected error."
            }
        )

@router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLoginRequest):
    """Login user with comprehensive error handling."""
    try:
        user = await authenticate_user(login_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id, "tenant_id": user.tenant_id},
            expires_delta=None
        )
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
    except DatabaseConnectionError as e:
        # 503 Service Unavailable - DB connection failed
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "database_connection_error",
                "message": "Unable to connect to database. Please try again later.",
                "details": str(e.message)
            }
        )
    except DatabaseTimeoutError as e:
        # 503 Service Unavailable - DB operation timed out
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "database_timeout",
                "message": "Database operation timed out. Please try again.",
                "details": str(e.message)
            }
        )
    except DatabaseQueryError as e:
        # 500 Internal Server Error - Query failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_query_error",
                "message": "A database error occurred during authentication.",
                "details": str(e.message)
            }
        )
    except DatabaseError as e:
        # 500 Internal Server Error - General DB error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "An unexpected database error occurred.",
                "details": str(e.message)
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like 401)
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred during login."
            }
        )


@router.post("/auth/forgot-password")
async def forgot_password(request: UserForgotPasswordRequest):
    """Request password reset token."""
    token = await create_password_reset_token(request.email)
    if token:
        # In production this would send email
        return {"message": "If email exists, a reset link has been sent."}
    return {"message": "If email exists, a reset link has been sent."}


@router.post("/auth/reset-password")
async def reset_password_endpoint(request: UserResetPasswordRequest):
    """Reset password with token."""
    success = await reset_password(request.token, request.new_password)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )
    return {"message": "Password updated successfully"}


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request with multi-tenant context."""
    prompt: str
    tenant_id: str = Field(..., description="Tenant ObjectId")
    user_id: str = Field(..., description="User UUID")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID (auto-generated if not provided)")


class ChatResponse(BaseModel):
    """Chat response with thread tracking."""
    response: str
    thread_id: str


class ConversationInfo(BaseModel):
    """Summary info for a conversation."""
    thread_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageInfo(BaseModel):
    """Message in a conversation."""
    role: str
    content: str
    timestamp: str
    activity: Optional[List[dict]] = []


# ============================================================================
# Agent Endpoints
# ============================================================================

def build_config(tenant_id: str, user_id: str, thread_id: str) -> dict:
    """Build LangGraph config with multi-tenant metadata."""
    return {
        "configurable": {
            "thread_id": thread_id,
        },
        "metadata": {
            "tenant_id": tenant_id,
            "user_id": user_id
        }
    }


@router.post("/v1/agent/run", response_model=ChatResponse)
async def run_agent(request: ChatRequest):
    """Run the supervisor agent workflow (sync mode) with context persistence."""
    session_start()
    
    # Generate thread_id if not provided
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # Build config with multi-tenant namespace
    config = build_config(request.tenant_id, request.user_id, thread_id)
    
    initial_state = {"messages": [HumanMessage(content=request.prompt)]}
    
    # Run with checkpointer for persistence
    async with get_checkpointer() as checkpointer:
        graph_with_memory = build_graph(checkpointer=checkpointer)
        # Ensure config with metadata is passed
        result = await graph_with_memory.ainvoke(initial_state, config)
    
    last_msg = result["messages"][-1].content
    return ChatResponse(response=last_msg, thread_id=thread_id)


async def stream_events(
    prompt: str,
    tenant_id: str,
    user_id: str,
    thread_id: str
) -> AsyncGenerator[str, None]:
    """Stream events from the LangGraph workflow with context persistence."""
    initial_state = {"messages": [HumanMessage(content=prompt)]}
    # Config is built here
    config = build_config(tenant_id, user_id, thread_id)
    
    # Send initial event with thread_id
    yield json.dumps({
        "content": {
            "sender": "Supervisor",
            "message": "Processing your request...",
            "node": "supervisor",
            "thread_id": thread_id
        }
    }) + "\n"
    
    last_content = ""
    
    import asyncio
    from langchain_core.messages import ToolMessage
    
    try:
        async with get_checkpointer() as checkpointer:
            # Checkpointer is attached here
            graph_with_memory = build_graph(checkpointer=checkpointer)
            
            # --- State Repair Start ---
            # Check if likely hanging tool call exists
            current_state = await graph_with_memory.aget_state(config)
            if current_state.values:
                messages = current_state.values.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                        # Inspect logic: If we are here, it means we are starting a NEW run.
                        # If the last message in DB is AI with tools, it means the tool execution 
                        # was interrupted (cancelled) and never wrote back the ToolMessage.
                        # We MUST inject a ToolMessage to satisfy the LLM's conversation validity constraints.
                        
                        repair_messages = []
                        for tool_call in last_msg.tool_calls:
                            repair_messages.append(ToolMessage(
                                tool_call_id=tool_call["id"],
                                content="Action cancelled by user.",
                                name=tool_call["name"]
                            ))
                        
                        if repair_messages:
                            await graph_with_memory.aupdate_state(config, {"messages": repair_messages})
                            print(f"INFO: Repaired dangling tool calls for thread {thread_id}")
            # --- State Repair End ---
            
            # Config passed here. 
            async for event in graph_with_memory.astream_events(initial_state, config, version="v2"):
                event_type = event.get("event", "")
                
                # Track node transitions
                if event_type == "on_chain_start":
                    node_name = event.get("name", "")
                    if node_name == "supervisor":
                        yield json.dumps({
                            "content": {
                                "sender": "Supervisor",
                                "message": "Executing supervisor node...",
                                "node": node_name
                            }
                        }) + "\n"
                
                # Capture tool calls
                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    
                    # 1. Handoff from Supervisor
                    yield json.dumps({
                        "content": {
                            "sender": "Supervisor",
                            "message": f"Delegating to {tool_name}...",
                            "node": "tools"
                        }
                    }) + "\n"
                    
                    # 2. Agent Starting (Keeps graph active on Agent)
                    sender = "Unknown Agent"
                    if "rate" in tool_name.lower() or "service" in tool_name.lower():
                        sender = "Serviceability Agent"
                    elif "book" in tool_name.lower():
                        sender = "Booking Agent"
                    elif "slim" in tool_name.lower():
                        sender = "SLIM Transport"
                        
                    yield json.dumps({
                        "content": {
                            "sender": sender,
                            "message": "Processing request...",
                            "node": "tools"
                        }
                    }) + "\n"
                
                # Capture tool results
                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = event.get("data", {}).get("output", "")
                    
                    # Determine sender based on tool name
                    sender = "Unknown Agent"
                    if "rate" in tool_name.lower() or "service" in tool_name.lower():
                        sender = "Serviceability Agent"
                    elif "book" in tool_name.lower():
                        sender = "Booking Agent"
                    elif "slim" in tool_name.lower():
                        sender = "SLIM Transport"
                    
                    if tool_output:
                        yield json.dumps({
                            "content": {
                                "sender": sender,
                                "message": str(tool_output)[:200] + "...",
                                "node": "carrier"
                            }
                        }) + "\n"
                
                # Capture final AI messages
                elif event_type == "on_chain_end":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict) and "messages" in output:
                        messages = output["messages"]
                        if messages:
                            last_msg = messages[-1]
                            if hasattr(last_msg, "content") and last_msg.content:
                                last_content = last_msg.content
        
        # Final response
        if last_content:
            yield json.dumps({
                "content": {
                    "sender": "Supervisor",
                    "message": last_content,
                    "node": "supervisor",
                    "final": True,
                    "thread_id": thread_id
                }
            }) + "\n"

    except asyncio.CancelledError:
        print(f"INFO: Request cancelled by client. Thread ID: {thread_id}")
        # Optionally perform cleanup here if needed, but the 'async with checkpointer' 
        # exit should handle connection release.
        # Reraise is important for FastAPI to know it was cancelled? 
        # Actually generator cancellation raises GeneratorExit or CancelledError inside.
        raise
    except Exception as e:
        print(f"ERROR: Stream failed: {e}")
        import traceback
        traceback.print_exc()
        # Don't swallow unexpected errors
        raise


@router.post("/v1/agent/stream")
async def stream_agent(request: ChatRequest):
    """Stream the supervisor agent workflow with SSE and context persistence."""
    session_start()
    
    thread_id = request.thread_id or str(uuid.uuid4())
    
    return StreamingResponse(
        stream_events(request.prompt, request.tenant_id, request.user_id, thread_id),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============================================================================
# Conversation History Endpoints
# ============================================================================

@router.get("/v1/conversations", response_model=List[ConversationInfo])
async def list_conversations(tenant_id: str, user_id: str):
    """
    List all conversations for a tenant/user.
    
    Queries the checkpoints table directly to get all unique thread_ids.
    """
    from agent.memory import DATABASE_URL
    from psycopg import AsyncConnection
    
    # Query unique thread_ids from checkpoints table using metadata
    import json
    metadata_filter = json.dumps({"tenant_id": tenant_id, "user_id": user_id})
    conversations = []
    
    query = """
        SELECT DISTINCT thread_id
        FROM checkpoints 
        WHERE metadata @> %s::jsonb
        ORDER BY thread_id DESC
        LIMIT 50
    """
    
    try:
        async with await AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (metadata_filter,))
                rows = await cur.fetchall()
                
                # Now get details for each thread
                async with get_checkpointer() as checkpointer:
                    for row in rows:
                        thread_id = row[0]
                        
                        # Get checkpoint
                        config = {"configurable": {"thread_id": thread_id}}
                        checkpoint_tuple = await checkpointer.aget_tuple(config)
                        

                        
                        if checkpoint_tuple:
                            checkpoint = checkpoint_tuple.checkpoint
                            messages = checkpoint.get("channel_values", {}).get("messages", [])
                            
                            # Get first user message as title
                            title = "New Conversation"
                            for msg in messages:
                                if isinstance(msg, HumanMessage):
                                    title = msg.content[:50] + ("..." if len(msg.content) > 50 else "")
                                    break
                            
                            conversations.append(ConversationInfo(
                                thread_id=thread_id,
                                title=title,
                                created_at=checkpoint.get("ts", ""),
                                updated_at=checkpoint.get("ts", ""),
                                message_count=len(messages)
                            ))
    except Exception as e:
        print(f"Error listing conversations: {e}")
        import traceback
        traceback.print_exc()
    
    return conversations


@router.get("/v1/conversations/{thread_id}", response_model=List[MessageInfo])
async def get_conversation(thread_id: str, tenant_id: str, user_id: str):
    """Get all messages in a conversation, including tool activity."""
    from langchain_core.messages import ToolMessage
    
    async with get_checkpointer() as checkpointer:
        # Get via thread_id
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        # Verify ownership via metadata (metadata is stored in checkpoint_tuple.metadata, NOT checkpoint.get("metadata"))
        if checkpoint_tuple:
            meta = checkpoint_tuple.metadata or {}
            # Check if user_id matches for ownership verification
            if meta.get("user_id") and meta.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
        
        if not checkpoint_tuple:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        raw_messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])
        
        # Process messages to aggregate activity
        processed_messages = []
        pending_activity = []
        
        for msg in raw_messages:
            # 1. Capture Tool Calls (from AI)
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    pending_activity.append({
                        "sender": "Supervisor",
                        "message": f"Calling {tool_name}...",
                        "state": "pending"
                    })
            
                # 2. Capture Tool Outputs (from Tool)
            elif isinstance(msg, ToolMessage):
                tool_name = msg.name or "unknown"
                sender = "Unknown Agent"
                if "rate" in tool_name.lower() or "service" in tool_name.lower():
                    sender = "Serviceability Agent"
                elif "book" in tool_name.lower():
                    sender = "Booking Agent"
                elif "slim" in tool_name.lower():
                    sender = "SLIM Transport"
                    
                pending_activity.append({
                    "sender": sender,
                    "message": str(msg.content)[:200] + ("..." if len(str(msg.content)) > 200 else ""),
                    "state": "done"
                })
            
            # 3. Capture AI Response (Result)
            elif isinstance(msg, AIMessage) and msg.content:
                # Attach collected activity to this assistant message
                processed_messages.append(MessageInfo(
                    role="assistant",
                    content=str(msg.content),
                    timestamp=getattr(msg, "timestamp", "") or "",
                    activity=pending_activity
                ))
                pending_activity = [] # Reset buffer
                
            # 4. Capture User Message
            elif isinstance(msg, HumanMessage):
                # If there's pending activity before a user message, attach it to a placeholder? 
                # Or just drop it? Ideally activity belongs to previous turn.
                # In standard flow, activity -> AI Message.
                if pending_activity:
                    # Creating a system/assistant message to hold the activity if no final response followed?
                    # For now, let's just clear typical pending activity or attach it to next?
                    # Let's attach to PREVIOUS message if possible? No.
                    pass
                    
                processed_messages.append(MessageInfo(
                    role="user",
                    content=str(msg.content),
                    timestamp=getattr(msg, "timestamp", "") or "",
                    activity=[]
                ))
        
        return processed_messages


@router.delete("/v1/conversations/{thread_id}")
async def delete_conversation(thread_id: str, tenant_id: str, user_id: str):
    """Delete a conversation and all its checkpoints."""
    from agent.memory import DATABASE_URL
    from psycopg import AsyncConnection
    
    import json
    metadata_filter = json.dumps({"tenant_id": tenant_id, "user_id": user_id})

    try:
        async with await AsyncConnection.connect(DATABASE_URL) as conn:
            # Delete from all checkpoint tables where metadata matches
            # Note: checkpoint_writes and checkpoint_blobs don't have metadata column usually? 
            # They refer to thread_id. If thread_id is unique to user (UUID generated by client/server), 
            # we can delete by thread_id IF we verify ownership first.
            
            # Verify ownership first
            await conn.execute(
                "SELECT 1 FROM checkpoints WHERE thread_id = %s AND metadata @> %s::jsonb LIMIT 1",
                (thread_id, metadata_filter)
            )
            if not await conn.fetchone():
                 raise HTTPException(status_code=404, detail="Conversation not found or access denied")

            await conn.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                (thread_id,)
            )
            await conn.execute(
                "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
                (thread_id,)
            )
            await conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = %s",
                (thread_id,)
            )
            await conn.commit()
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")
    
    return {"status": "deleted", "thread_id": thread_id}


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


app.include_router(router)
