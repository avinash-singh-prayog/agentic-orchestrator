"""
Booking Agent Settings.

Environment-based configuration using pydantic-settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class BookingAgentSettings(BaseSettings):
    """Configuration settings for the booking agent."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Logging
    log_level: str = "INFO"

    # ==========================================================================
    # Order V2 API Settings
    # ==========================================================================
    
    # Base URL for Order V2 API - MUST be set via BOOKING_AGENT_ORDER_API_URL env var
    order_api_url: str
    
    # API timeout in seconds
    order_api_timeout: int = 30
    
    # Max retries for API calls
    order_api_max_retries: int = 3
    
    # Default tenant ID (optional)
    default_tenant_id: str = ""
    
    # Default user ID (optional)
    default_user_id: str = ""
    
    # Source identifier
    source: str = "agentic-orchestrator"

    # ==========================================================================
    # LLM Settings
    # ==========================================================================
    
    # LLM model for order extraction - Use openai/gpt-oss-120b:free instead of gpt-4o-mini
    # Default removed - must be set via BOOKING_AGENT_LLM_MODEL env var
    llm_model: str = ""  # Configured via environment
    
    # LLM temperature
    llm_temperature: float = 0.1
    
    # Max tokens for LLM response
    llm_max_tokens: int = 500

    # ==========================================================================
    # Business Rules
    # ==========================================================================
    
    # Default payment type
    default_payment_type: str = "PREPAID"
    
    # Default currency
    default_currency: str = "INR"
    
    # Auto-confirm orders
    auto_confirm: bool = True

    model_config = {
        "env_prefix": "BOOKING_AGENT_",
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "extra": "ignore"
    }


# Global settings instance
settings = BookingAgentSettings()
