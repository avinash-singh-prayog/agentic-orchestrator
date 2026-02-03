"""
Transaction RCA Agent Settings.

Environment-based configuration using pydantic-settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class TransactionRCAAgentSettings(BaseSettings):
    """Configuration settings for the transaction RCA agent."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 3045  # PineLabs deployment port
    debug: bool = False

    # Logging
    log_level: str = "INFO"

    # LLM Model
    transaction_rca_agent_llm: str = "openrouter/openai/gpt-5.2"

    # Database
    database_url: str = ""  # Will be read from DATABASE_URL env var

    model_config = {
        "env_prefix": "TRANSACTION_RCA_AGENT_",
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "extra": "ignore",
    }


# Global settings instance
settings = TransactionRCAAgentSettings()
