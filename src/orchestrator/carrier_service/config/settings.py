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

    # ==========================================================================
    # Carrier Settings
    # ==========================================================================

    # DHL (placeholder)
    dhl_enabled: bool = False
    dhl_api_key: str = ""

    # India Post (placeholder)
    india_post_enabled: bool = False
    india_post_api_key: str = ""


    # Aramex
    aramex_enabled: bool = False
    aramex_base_url: str = "https://ws.aramex.net"
    aramex_username: str = ""
    aramex_password: str = ""
    aramex_account_number: str = ""
    aramex_account_pin: str = ""
    aramex_account_entity: str = "BOM"
    aramex_account_country_code: str = "IN"
    aramex_source: int = 24
    aramex_timeout: int = 30
    aramex_max_retries: int = 3
    aramex_sandbox_mode: bool = True  # Default to sandbox for safety

    # ==========================================================================
    # Business Rules
    # ==========================================================================
    auto_book_cheapest: bool = True
    max_auto_approval_limit: float = 5000.0

    class Config:
        env_prefix = "CARRIER_"
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = CarrierServiceSettings()
