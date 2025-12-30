"""
Personal Assistant Agent Configuration.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 9006
    log_level: str = "INFO"
    
    # LLM Configuration
    llm_model: str = "openrouter/openai/gpt-4o-mini"
    openrouter_api_key: str = ""
    groq_api_key: str = ""
    
    # SLIM Transport
    slim_endpoint: str = "http://orchestrator-slim:46357"
    slim_topic: str = "agents.personal.v1"
    default_message_transport: str = "SLIM"
    
    # MCP Server Endpoints (SSE transport)
    weather_mcp_url: str = "http://weather-mcp:8000/sse"
    websearch_mcp_url: str = "http://websearch-mcp:8000/sse"
    
    # Directory Service
    directory_service_addr: str = "directory-service:8888"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
