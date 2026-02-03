"""
Supervisor Agent API.

Entry point for the supervisor agent with factory initialization.
Multi-tenant chat context persistence via PostgreSQL checkpointer.
"""

import json
import uuid
import logging
from typing import AsyncGenerator, Optional, List, Literal, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, APIRouter, Request, Form, File as FastAPIFile, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.document_processor import process_attachment

logger = logging.getLogger(__name__)

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
    get_user_llm_config,
    update_user_llm_config,
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
router = APIRouter(prefix="/supervisor-pinelabs")

# Include OAuth router
from app import oauth
router.include_router(oauth.router)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for validation errors to provide better error messages
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle 422 validation errors with detailed logging."""
    logger.error(f"Validation error on {request.url.path}: {exc.errors()}")
    # Log request body for debugging (truncate if too large)
    try:
        body = await request.body()
        body_str = body.decode('utf-8')[:2000]  # First 2000 chars
        logger.error(f"Request body (truncated): {body_str[:500]}...")
        # Try to parse and show attachment info
        import json
        try:
            body_json = json.loads(body_str)
            if 'attachments' in body_json:
                att_info = []
                for att in body_json.get('attachments', []):
                    att_info.append(f"  - {att.get('name', 'unknown')}: type={att.get('file_type', 'unknown')}, has_content={bool(att.get('content'))}, content_len={len(att.get('content', '')) if att.get('content') else 0}")
                logger.error(f"Attachments info:\n" + "\n".join(att_info))
        except:
            pass
    except Exception as e:
        logger.error(f"Error reading request body: {e}")
    
    # Return standard FastAPI validation error response
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )


# Note: Health check logging is reduced by:
# 1. Increasing interval in frontend Navigation component (5 minutes instead of 30 seconds)
# 2. Uvicorn access logs can be further filtered via command line options in run-dev.sh


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

class FileAttachment(BaseModel):
    """File attachment model."""
    id: str
    name: str
    type: str
    size: int
    file_type: Literal["image", "text"] = Field(..., description="File type classification for routing")
    content: Optional[Union[str, bytes]] = Field(default=None, description="File content as bytes (from FormData) or base64 string (backward compatibility)")
    
    class Config:
        # Allow extra fields for backward compatibility
        extra = "ignore"


class ChatRequest(BaseModel):
    """Chat request with multi-tenant context."""
    prompt: str
    tenant_id: str = Field(..., description="Tenant ObjectId")
    user_id: str = Field(..., description="User UUID")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID (auto-generated if not provided)")
    attachments: Optional[List[FileAttachment]] = Field(None, description="File attachments")


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
    attachments: Optional[List[FileAttachment]] = None


class LLMConfigRequest(BaseModel):
    """LLM configuration request."""
    provider: Literal["openai", "anthropic", "google", "groq", "openrouter"]
    model: str
    api_key: Optional[str] = None


class LLMConfigResponse(BaseModel):
    """LLM configuration response."""
    provider: Optional[str] = None
    model: Optional[str] = None
    has_api_key: bool = False
    updated_at: Optional[str] = None


class LLMConfigTestRequest(BaseModel):
    """LLM configuration test request."""
    provider: Literal["openai", "anthropic", "google", "groq", "openrouter"]
    model: str
    api_key: str


# ============================================================================
# Agent Endpoints
# ============================================================================

def build_config(tenant_id: str, user_id: str, thread_id: str, llm_config: Optional[dict] = None) -> dict:
    """Build LangGraph config with multi-tenant metadata and LLM configuration."""
    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "metadata": {
            "tenant_id": tenant_id,
            "user_id": user_id
        }
    }
    
    # Add LLM config if provided
    if llm_config:
        logger.info(f"[build_config] Adding LLM config to configurable: {llm_config.get('provider')}/{llm_config.get('model')}")
        config["configurable"]["llm_config"] = llm_config
    else:
        logger.warning(f"[build_config] No LLM config provided for user {user_id}")
    
    return config


def build_message_with_attachments(prompt: str, attachments: Optional[List[FileAttachment]]) -> HumanMessage:
    """
    Build a HumanMessage with text and/or image content from attachments.
    
    For text files: Includes extracted text in the prompt.
    For images: Includes base64 image data for Vision GPT.
    """
    logger.info(f"[build_message_with_attachments] Building message with prompt: {prompt[:50]}..., attachments: {len(attachments) if attachments else 0}")
    
    if not attachments or len(attachments) == 0:
        logger.info("[build_message_with_attachments] No attachments, returning simple message")
        return HumanMessage(content=prompt)
    
    # Separate text and image attachments
    text_content_parts = []
    image_content_parts = []
    
    # Process each attachment
    for attachment in attachments:
        try:
            logger.info(f"[build_message_with_attachments] Processing attachment: {attachment.name} (type: {attachment.type}, size: {attachment.size}, classification: {attachment.file_type})")
            
            # Validate attachment has content
            if not attachment.content:
                logger.warning(f"[build_message_with_attachments] Attachment {attachment.name} has no content, skipping")
                text_content_parts.append(f"\n\n[File: {attachment.name} - No content provided]")
                continue
            
            logger.info(f"[build_message_with_attachments] Attachment {attachment.name} has content: {len(attachment.content)} bytes (type: {type(attachment.content)})")
            
            processed_content, content_type = process_attachment(
                attachment.id,
                attachment.name,
                attachment.type,
                attachment.size,
                attachment.file_type,
                attachment.content
            )
            
            logger.info(f"[build_message_with_attachments] Successfully processed {attachment.name} as {content_type}, content length: {len(processed_content) if processed_content else 0}")
            
            if content_type == "text":
                # Add text content to prompt
                text_content_parts.append(f"\n\n[File: {attachment.name}]\n{processed_content}")
                logger.info(f"[build_message_with_attachments] Added text content from {attachment.name} to message")
            elif content_type == "image":
                # Add image for Vision GPT
                # LangChain/LiteLLM format: list of dicts with type and data
                image_content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{attachment.type.split('/')[-1]};base64,{processed_content}"
                    }
                })
                logger.info(f"[build_message_with_attachments] Added image content from {attachment.name} to message")
        except Exception as e:
            logger.error(f"[build_message_with_attachments] Error processing attachment {attachment.name}: {e}", exc_info=True)
            # Continue with other attachments
            text_content_parts.append(f"\n\n[File: {attachment.name} - Error processing: {str(e)}]")
    
    # Build final content
    if image_content_parts:
        # If we have images, use multi-modal format
        # LiteLLM/ChatLiteLLM supports list of content parts
        content_parts = []
        
        # Add text prompt first
        full_text = prompt + "".join(text_content_parts)
        if full_text.strip():
            content_parts.append({"type": "text", "text": full_text})
        
        # Add images
        content_parts.extend(image_content_parts)
        
        logger.info(f"[build_message_with_attachments] Returning multi-modal message with {len(content_parts)} parts (text + {len(image_content_parts)} images)")
        return HumanMessage(content=content_parts)
    else:
        # Text only - include extracted text in prompt
        full_prompt = prompt + "".join(text_content_parts)
        logger.info(f"[build_message_with_attachments] Returning text-only message, total length: {len(full_prompt)} characters")
        logger.debug(f"[build_message_with_attachments] Message preview: {full_prompt[:200]}...")
        return HumanMessage(content=full_prompt)


@router.post("/v1/agent/run", response_model=ChatResponse)
async def run_agent(request: ChatRequest):
    """Run the supervisor agent workflow (sync mode) with context persistence."""
    session_start()
    
    # Generate thread_id if not provided
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # Fetch user's LLM configuration
    llm_config = None
    try:
        llm_config = await get_user_llm_config(request.user_id)
    except Exception as e:
        logger.warning(f"Failed to fetch LLM config for user {request.user_id}: {e}. Using default.")
    
    # Build config with multi-tenant namespace and LLM config
    config = build_config(request.tenant_id, request.user_id, thread_id, llm_config)
    
    # Build message with attachments
    user_message = build_message_with_attachments(request.prompt, request.attachments)
    initial_state = {"messages": [user_message]}
    
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
    thread_id: str,
    attachments: Optional[List[FileAttachment]] = None
) -> AsyncGenerator[str, None]:
    """Stream events from the LangGraph workflow with context persistence."""
    logger.info(f"[stream_events] Starting stream - prompt: {prompt[:50]}..., attachments: {len(attachments) if attachments else 0}")
    
    # Fetch user's LLM configuration
    llm_config = None
    try:
        llm_config = await get_user_llm_config(user_id)
        if llm_config:
            logger.info(f"[stream_events] Using user LLM config: {llm_config.get('provider')}/{llm_config.get('model')}")
    except Exception as e:
        logger.warning(f"[stream_events] Failed to fetch LLM config for user {user_id}: {e}. Using default.")
    
    # Build message with attachments (with error handling)
    try:
        user_message = build_message_with_attachments(prompt, attachments)
        logger.info(f"[stream_events] Successfully built message with attachments. Content type: {type(user_message.content)}, length: {len(str(user_message.content)) if isinstance(user_message.content, str) else 'list'}")
    except Exception as e:
        logger.error(f"[stream_events] Error building message with attachments: {e}", exc_info=True)
        # Fallback to simple message if attachment processing fails
        user_message = HumanMessage(content=prompt)
        if attachments:
            # Add note about attachment processing failure
            logger.warning(f"[stream_events] Falling back to simple message due to attachment processing error")
            user_message = HumanMessage(content=f"{prompt}\n\n[Note: Some attachments could not be processed]")
    
    initial_state = {"messages": [user_message]}
    config = build_config(tenant_id, user_id, thread_id, llm_config)
    
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
                    tool_name_lower = tool_name.lower()
                    
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
                    # Check for Transaction RCA Agent first (most specific)
                    if ("transaction" in tool_name_lower and "rca" in tool_name_lower) or "transaction_rca" in tool_name_lower:
                        sender = "Transaction RCA Agent"
                    elif "slim" in tool_name_lower:
                        sender = "SLIM Transport"
                    
                    # Log for debugging (using module-level logger)
                    logger.info(f"Tool: {tool_name}, Mapped sender: {sender}")
                        
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
                    tool_name_lower = tool_name.lower()
                    tool_output = event.get("data", {}).get("output", "")
                    
                    # Determine sender based on tool name
                    sender = "Unknown Agent"
                    # Check for Transaction RCA Agent first (most specific)
                    if ("transaction" in tool_name_lower and "rca" in tool_name_lower) or "transaction_rca" in tool_name_lower:
                        sender = "Transaction RCA Agent"
                    elif "slim" in tool_name_lower:
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
async def stream_agent(request: Request):
    """Stream the supervisor agent workflow with SSE and context persistence.
    
    Accepts both JSON (for backward compatibility) and FormData (for file uploads).
    """
    session_start()
    
    content_type = request.headers.get("content-type", "")
    
    if content_type.startswith("multipart/form-data"):
        # Handle FormData - files sent directly (no base64)
        form_data = await request.form()
        
        prompt = form_data.get("prompt", "")
        tenant_id = form_data.get("tenant_id", "")
        user_id = form_data.get("user_id", "")
        thread_id = form_data.get("thread_id") or str(uuid.uuid4())
        
        logger.info(f"[stream_agent] Received FormData request - prompt: {prompt[:50]}..., tenant_id: {tenant_id}, user_id: {user_id}")
        
        # Extract files from form data
        attachments = []
        
        # First, log all form data keys to debug
        all_keys = list(form_data.keys())
        logger.info(f"[stream_agent] All form data keys: {all_keys}")
        
        # Try to find files - check both indexed pattern and direct file keys
        index = 0
        found_files = False
        
        # Method 1: Check for indexed files (file_0, file_1, etc.)
        while f"file_{index}" in form_data:
            found_files = True
            file_obj = form_data[f"file_{index}"]
            logger.info(f"[stream_agent] Found file_{index}, type: {type(file_obj)}, is UploadFile: {isinstance(file_obj, UploadFile)}, is StarletteUploadFile: {isinstance(file_obj, StarletteUploadFile)}")
            
            # Check for both FastAPI UploadFile and Starlette UploadFile
            if isinstance(file_obj, (UploadFile, StarletteUploadFile)) or hasattr(file_obj, 'read') and hasattr(file_obj, 'filename'):
                # Read file content as bytes - no base64 conversion needed!
                file_content = await file_obj.read()
                
                file_id = form_data.get(f"file_{index}_id", str(uuid.uuid4()))
                file_name = form_data.get(f"file_{index}_name", file_obj.filename or "unknown")
                file_type = form_data.get(f"file_{index}_type", file_obj.content_type or "application/octet-stream")
                file_size = int(form_data.get(f"file_{index}_size", len(file_content)))
                file_type_class = form_data.get(f"file_{index}_file_type", "text")
                
                logger.info(f"[stream_agent] Processing file {index}: {file_name} (type: {file_type}, size: {file_size} bytes, classification: {file_type_class}, content length: {len(file_content)} bytes)")
                
                if len(file_content) == 0:
                    logger.warning(f"[stream_agent] File {file_name} has zero bytes!")
                
                attachments.append(FileAttachment(
                    id=file_id,
                    name=file_name,
                    type=file_type,
                    size=file_size,
                    file_type=file_type_class,
                    content=file_content  # Send bytes directly - document_processor will handle it
                ))
            else:
                logger.warning(f"[stream_agent] file_{index} is not an UploadFile, it's {type(file_obj)}")
            index += 1
        
        # Method 2: Check for any UploadFile objects directly (in case frontend uses different keys)
        if not found_files:
            logger.info("[stream_agent] No indexed files found, checking for any UploadFile objects...")
            for key, value in form_data.items():
                # Check for both FastAPI UploadFile and Starlette UploadFile, or any object with read() and filename
                if isinstance(value, (UploadFile, StarletteUploadFile)) or (hasattr(value, 'read') and hasattr(value, 'filename')):
                    logger.info(f"[stream_agent] Found UploadFile with key '{key}': {value.filename}")
                    file_content = await value.read()
                    file_name = value.filename or "unknown"
                    file_type = value.content_type or "application/octet-stream"
                    
                    # Try to get metadata from form data with this key as prefix
                    file_id = form_data.get(f"{key}_id", str(uuid.uuid4()))
                    file_size = int(form_data.get(f"{key}_size", len(file_content)))
                    file_type_class = form_data.get(f"{key}_file_type", "text")
                    
                    logger.info(f"[stream_agent] Processing file from key '{key}': {file_name} (type: {file_type}, size: {file_size} bytes)")
                    
                    attachments.append(FileAttachment(
                        id=file_id,
                        name=file_name,
                        type=file_type,
                        size=file_size,
                        file_type=file_type_class,
                        content=file_content
                    ))
        
        logger.info(f"[stream_agent] Total attachments extracted: {len(attachments)}")
        
        if len(attachments) == 0:
            logger.warning("[stream_agent] No attachments found in FormData request. Checking form data keys...")
            form_keys = list(form_data.keys())
            logger.warning(f"[stream_agent] Form data keys: {form_keys}")
            
            # Also check if files are present with different key patterns
            file_keys = [k for k in form_keys if 'file' in k.lower()]
            if file_keys:
                logger.warning(f"[stream_agent] Found file-related keys: {file_keys}")
                for key in file_keys:
                    value = form_data.get(key)
                    logger.warning(f"[stream_agent] Key '{key}': type={type(value)}, value={str(value)[:100] if value else 'None'}")
        
        request_attachments = attachments if attachments else None
    else:
        # Handle JSON (backward compatibility)
        try:
            json_data = await request.json()
            chat_request = ChatRequest(**json_data)
            prompt = chat_request.prompt
            tenant_id = chat_request.tenant_id
            user_id = chat_request.user_id
            thread_id = chat_request.thread_id or str(uuid.uuid4())
            request_attachments = chat_request.attachments
            
            # Filter out attachments without content
            if request_attachments:
                valid_attachments = [att for att in request_attachments if att.content]
                if len(valid_attachments) < len(request_attachments):
                    logger.warning(f"Filtered out {len(request_attachments) - len(valid_attachments)} attachments without content")
                request_attachments = valid_attachments if valid_attachments else None
        except Exception as e:
            logger.error(f"Error parsing JSON request: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")
    
    try:
        return StreamingResponse(
            stream_events(prompt, tenant_id, user_id, thread_id, request_attachments),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        logger.error(f"Error in stream_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Streaming error: {str(e)}")


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
                                    # Handle both string and list content (multi-modal messages)
                                    if isinstance(msg.content, list):
                                        # Extract text from multi-modal content
                                        text_parts = []
                                        for part in msg.content:
                                            if isinstance(part, dict) and part.get("type") == "text":
                                                text_parts.append(part.get("text", ""))
                                            elif isinstance(part, str):
                                                text_parts.append(part)
                                        content_text = " ".join(text_parts) if text_parts else "Message with attachments"
                                    else:
                                        content_text = str(msg.content)
                                    
                                    # Truncate to 50 characters for title
                                    if len(content_text) > 50:
                                        title = content_text[:50] + "..."
                                    else:
                                        title = content_text
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
                tool_name_lower = tool_name.lower()
                sender = "Unknown Agent"
                # Check for Transaction RCA Agent first (most specific)
                if ("transaction" in tool_name_lower and "rca" in tool_name_lower) or "transaction_rca" in tool_name_lower:
                    sender = "Transaction RCA Agent"
                elif "slim" in tool_name_lower:
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
    """Health check endpoint - minimal logging."""
    # Health checks are frequent, so we don't log them
    return {"status": "ok"}


# ============================================================================
# LLM Settings Endpoints
# ============================================================================

# Available providers and models
AVAILABLE_PROVIDERS = {
    "openai": {
        "models": ["gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4-turbo", "gpt-4o"],
        "api_key_prefix": "sk-"
    },
    "anthropic": {
        "models": ["claude-opus-4.5", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "api_key_prefix": "sk-ant-"
    },
    "google": {
        "models": ["gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"],
        "api_key_prefix": "AI"
    },
    "groq": {
        "models": ["meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct", "llama-3.3-70b-scout", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "api_key_prefix": "gsk_"
    },
    "openrouter": {
        "models": ["google/gemini-2.5-flash", "anthropic/claude-opus-4.5", "x-ai/grok-4.1-fast", "openai/gpt-oss-120b", "minimax/minimax-m2.1", "google/gemini-2.5-flash-lite", "openai/gpt-5.2", "anthropic/claude-3.5-sonnet"],
        "api_key_prefix": "sk-or-"
    }
}

def validate_model_string(provider: str, model: str) -> str:
    """Validate and construct LiteLLM model string."""
    if provider == "openrouter":
        # OpenRouter models must always have openrouter/ prefix
        # Even if model has slash (e.g., "google/gemini-2.5-flash"), we need "openrouter/google/gemini-2.5-flash"
        if model.startswith("openrouter/"):
            return model
        else:
            return f"openrouter/{model}"
    elif provider == "groq":
        # Groq models may need meta-llama/ prefix for certain models
        if model.startswith("meta-llama/"):
            return f"groq/{model}"
        elif "/" in model:
            return f"groq/{model}"
        else:
            # For llama-4 models, add meta-llama/ prefix
            if model.startswith("llama-4"):
                return f"groq/meta-llama/{model}"
            else:
                return f"groq/{model}"
    else:
        # Standard format: provider/model
        return f"{provider}/{model}"

def validate_api_key_format(provider: str, api_key: str) -> bool:
    """Basic validation of API key format."""
    if not api_key or len(api_key) < 10:
        return False
    
    provider_info = AVAILABLE_PROVIDERS.get(provider)
    if provider_info:
        prefix = provider_info["api_key_prefix"]
        # For Google, API keys start with "AI" but can be longer
        if provider == "google":
            return api_key.startswith(prefix)
        else:
            return api_key.startswith(prefix)
    
    return True  # Allow unknown providers

@router.get("/v1/settings/llm-config", response_model=LLMConfigResponse)
async def get_llm_config(user_id: str):
    """Get user's current LLM configuration."""
    try:
        config = await get_user_llm_config(user_id)
        
        if not config:
            return LLMConfigResponse(
                provider=None,
                model=None,
                has_api_key=False,
                updated_at=None
            )
        
        return LLMConfigResponse(
            provider=config["provider"],
            model=config["model"],
            has_api_key=bool(config.get("api_key")),
            updated_at=config.get("updated_at")
        )
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
        logger.error(f"Error getting LLM config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Failed to retrieve LLM configuration."
            }
        )

@router.post("/v1/settings/llm-config")
async def update_llm_config(request: LLMConfigRequest, user_id: str):
    """Update user's LLM configuration."""
    try:
        logger.info(f"Update LLM config request for user {user_id}: provider={request.provider}, model={request.model}, api_key_provided={bool(request.api_key)}")
        
        # If API key is provided, validate its format
        if request.api_key:
            logger.info(f"API key provided, validating format for provider {request.provider}")
            if not validate_api_key_format(request.provider, request.api_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_api_key_format",
                        "message": f"API key format is invalid for {request.provider}. Expected format: {AVAILABLE_PROVIDERS.get(request.provider, {}).get('api_key_prefix', 'N/A')}..."
                    }
                )
            logger.info(f"API key format validated successfully, will save to database")
        else:
            # If API key is not provided, try to reuse existing one from database
            logger.info(f"No API key provided, checking database for existing key for user {user_id}")
            existing_config = await get_user_llm_config(user_id)
            
            if existing_config:
                existing_api_key = existing_config.get("api_key", "")
                existing_provider = existing_config.get("provider")
                logger.info(f"Found existing config: provider={existing_provider}, has_api_key={bool(existing_api_key)}, api_key_length={len(existing_api_key) if existing_api_key else 0}")
                
                # Check if we have a valid (non-empty) API key for the requested provider
                if existing_api_key and existing_api_key.strip():
                    if existing_provider == request.provider:
                        # Same provider - reuse the existing API key
                        request.api_key = existing_api_key
                        logger.info(f"Reusing existing API key for user {user_id} when switching to {request.provider}/{request.model}")
                    else:
                        # Different provider - need new API key for this provider
                        logger.warning(f"User {user_id} switching from {existing_provider} to {request.provider}, requires new API key")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "error": "api_key_required",
                                "message": f"API key is required when switching to provider {request.provider}. Please provide an API key for {request.provider}."
                            }
                        )
                else:
                    # No existing API key or empty API key - require one
                    logger.warning(f"No valid API key found in database for user {user_id}, provider {request.provider}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "api_key_required",
                            "message": f"API key is required for provider {request.provider}. Please provide an API key."
                        }
                    )
            else:
                # No existing config - require API key
                logger.warning(f"No existing config found for user {user_id}, requires API key")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "api_key_required",
                        "message": f"API key is required for provider {request.provider}. Please provide an API key."
                    }
                )
        
        # Validate model
        provider_info = AVAILABLE_PROVIDERS.get(request.provider)
        if provider_info and request.model not in provider_info["models"]:
            # Allow custom models but log a warning
            logger.warning(f"User {user_id} using custom model {request.model} for provider {request.provider}")
        
        # Update configuration
        success = await update_user_llm_config(
            user_id,
            request.provider,
            request.model,
            request.api_key
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "update_failed",
                    "message": "Failed to update LLM configuration."
                }
            )
        
        return {
            "status": "success",
            "message": "LLM configuration updated successfully"
        }
    except HTTPException:
        raise
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
        logger.error(f"Error updating LLM config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Failed to update LLM configuration."
            }
        )

@router.post("/v1/settings/llm-config/test")
async def test_llm_config(request: LLMConfigTestRequest):
    """Test LLM configuration with a simple API call."""
    try:
        # Validate API key format
        if not validate_api_key_format(request.provider, request.api_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_api_key_format",
                    "message": f"API key format is invalid for {request.provider}."
                }
            )
        
        # Construct model string
        model_string = validate_model_string(request.provider, request.model)
        
        # Test with a simple LLM call
        from langchain_community.chat_models import ChatLiteLLM
        from langchain_core.messages import HumanMessage
        
        # Set API key in environment temporarily (LiteLLM reads from env)
        import os
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY"
        }
        
        env_var = env_var_map.get(request.provider)
        if not env_var:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "unsupported_provider",
                    "message": f"Provider {request.provider} is not supported for testing."
                }
            )
        
        # Save original value
        original_key = os.environ.get(env_var)
        
        try:
            # Set temporary API key
            os.environ[env_var] = request.api_key
            
            # Create LLM instance
            llm = ChatLiteLLM(
                model=model_string,
                temperature=0,
                max_tokens=10,
                model_kwargs={
                    "num_retries": 1,
                    "timeout": 10,
                }
            )
            
            # Test with a simple message
            response = await llm.ainvoke([HumanMessage(content="Say 'test'")])
            
            return {
                "status": "success",
                "message": "LLM configuration test successful",
                "response_preview": str(response.content)[:100]
            }
        except Exception as e:
            error_str = str(e)
            logger.error(f"LLM test failed: {e}", exc_info=True)
            
            # Provide user-friendly error messages
            if "401" in error_str or "unauthorized" in error_str.lower():
                error_msg = "Invalid API key. Please check your API key and try again."
            elif "429" in error_str or "rate limit" in error_str.lower():
                error_msg = "Rate limit exceeded. Please try again later."
            elif "402" in error_str or "credits" in error_str.lower():
                error_msg = "Insufficient credits. Please add credits to your account."
            elif "timeout" in error_str.lower():
                error_msg = "Request timed out. Please check your network connection."
            else:
                error_msg = f"Test failed: {error_str[:200]}"
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "test_failed",
                    "message": error_msg
                }
            )
        finally:
            # Restore original value
            if original_key:
                os.environ[env_var] = original_key
            elif env_var in os.environ:
                del os.environ[env_var]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing LLM config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Failed to test LLM configuration."
            }
        )

@router.get("/v1/settings/llm-config/available")
async def get_available_models():
    """Get list of available providers and models."""
    return {
        "providers": {
            provider: {
                "models": info["models"],
                "api_key_prefix": info["api_key_prefix"]
            }
            for provider, info in AVAILABLE_PROVIDERS.items()
        }
    }


app.include_router(router)
