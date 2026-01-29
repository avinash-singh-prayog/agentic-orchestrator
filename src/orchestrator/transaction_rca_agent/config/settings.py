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
    port: int = 9006
    debug: bool = False

    # Logging
    log_level: str = "INFO"

    # LLM Model
    transaction_rca_agent_llm: str = "openrouter/openai/gpt-5.2"

    model_config = {
        "env_prefix": "TRANSACTION_RCA_AGENT_",
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "extra": "ignore",
    }


# Global settings instance
settings = TransactionRCAAgentSettings()
