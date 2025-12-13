"""
Carrier Service Settings.

Environment-based configuration using pydantic-settings.
"""

from pydantic_settings import BaseSettings


class CarrierServiceSettings(BaseSettings):
    """Configuration settings for the carrier service."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Logging
    log_level: str = "INFO"

    # Carrier settings
    mock_carrier_enabled: bool = True
    dhl_enabled: bool = False
    dhl_api_key: str = ""
    india_post_enabled: bool = False
    india_post_api_key: str = ""

    # Business rules
    auto_book_cheapest: bool = True
    max_auto_approval_limit: float = 5000.0

    class Config:
        env_prefix = "CARRIER_"
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = CarrierServiceSettings()
