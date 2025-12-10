"""
Configuration Management

Centralized configuration loading using Pydantic Settings.
All configuration is loaded from environment variables.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # LLM Configuration
    supervisor_llm: str = Field(
        default="openai/gpt-4-turbo",
        description="LLM model for the Supervisor agent",
    )
    rate_agent_llm: str = Field(
        default="groq/llama-3.1-70b-versatile",
        description="LLM model for the Rate agent",
    )
    service_agent_llm: str = Field(
        default="ollama/mistral",
        description="LLM model for the Serviceability agent",
    )
    carrier_agent_llm: str = Field(
        default="openai/gpt-4-turbo",
        description="LLM model for the Carrier agent",
    )
    
    # Transport Configuration
    default_message_transport: str = Field(
        default="SLIM",
        description="Message transport protocol (SLIM or NATS)",
    )
    transport_server_endpoint: str = Field(
        default="http://localhost:46357",
        description="Transport server endpoint",
    )
    
    # HITL Configuration
    max_auto_approval_limit: float = Field(
        default=5000.0,
        description="Maximum order value for auto-approval (USD)",
    )
    
    # Identity Service
    identity_service_type: str = Field(
        default="local",
        description="Identity service type (local or agntcy)",
    )
    identity_service_url: str | None = Field(
        default=None,
        description="AGNTCY Identity Service URL",
    )
    identity_service_api_key: str | None = Field(
        default=None,
        description="AGNTCY Identity Service API key",
    )
    
    # Database (PostgreSQL)
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="orchestrator")
    postgres_password: str = Field(default="orchestrator_secret")
    postgres_db: str = Field(default="orchestrator")
    
    # Observability
    otlp_http_endpoint: str = Field(
        default="http://localhost:4318",
        description="OpenTelemetry collector HTTP endpoint",
    )
    enable_tracing: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing",
    )
    
    # Service Ports
    supervisor_port: int = Field(default=8000)
    serviceability_agent_port: int = Field(default=9001)
    rate_agent_port: int = Field(default=9002)
    carrier_agent_port: int = Field(default=9003)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    @property
    def postgres_dsn(self) -> str:
        """Get PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
