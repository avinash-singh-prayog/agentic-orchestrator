"""
Aramex Configuration.

Dataclass for Aramex API credentials and settings.
"""

from dataclasses import dataclass

from orchestrator.carrier_service.config.settings import settings


@dataclass
class AramexConfig:
    """Aramex API configuration."""

    enabled: bool
    base_url: str
    username: str
    password: str
    account_number: str
    account_pin: str
    account_entity: str
    account_country_code: str
    source: int
    timeout: int
    max_retries: int
    sandbox_mode: bool

    @classmethod
    def from_settings(cls) -> "AramexConfig":
        """Create config from application settings."""
        base_url = settings.aramex_base_url
        if settings.aramex_sandbox_mode:
            base_url = "https://ws.dev.aramex.net"

        return cls(
            enabled=settings.aramex_enabled,
            base_url=base_url,
            username=settings.aramex_username,
            password=settings.aramex_password,
            account_number=settings.aramex_account_number,
            account_pin=settings.aramex_account_pin,
            account_entity=settings.aramex_account_entity,
            account_country_code=settings.aramex_account_country_code,
            source=settings.aramex_source,
            timeout=settings.aramex_timeout,
            max_retries=settings.aramex_max_retries,
            sandbox_mode=settings.aramex_sandbox_mode,
        )
