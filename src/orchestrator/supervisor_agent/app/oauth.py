"""
OAuth 2.0 Provider Module.

Vendor-agnostic OAuth implementation supporting Google (and future providers).
Uses authlib for OAuth 2.0 flow handling.
"""
import os
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from authlib.integrations.httpx_client import AsyncOAuth2Client
from psycopg import AsyncConnection

logger = logging.getLogger("oauth")

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "").strip('"').strip("'")

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/supervisor-agent/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@dataclass
class OAuthTokens:
    """OAuth token response."""
    access_token: str
    refresh_token: Optional[str]
    token_type: str
    expires_at: Optional[datetime]
    scopes: list[str]
    id_token: Optional[str] = None


@dataclass  
class OAuthUserInfo:
    """User info from OAuth provider."""
    provider: str
    provider_user_id: str
    email: str
    name: Optional[str]
    picture: Optional[str]


class OAuthProvider(ABC):
    """Abstract base class for OAuth providers (vendor-agnostic design)."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'google', 'apple')."""
        ...
    
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Get the OAuth authorization URL."""
        ...
    
    @abstractmethod
    async def handle_callback(self, code: str) -> tuple[OAuthTokens, OAuthUserInfo]:
        """Exchange authorization code for tokens and user info."""
        ...
    
    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired access token."""
        ...


class GoogleOAuthProvider(OAuthProvider):
    """
    Google OAuth 2.0 implementation.
    
    Scopes requested:
    - openid, email, profile: Basic user info for sign-in
    - calendar: Google Calendar access (for Personal Assistant)
    - gmail.modify: Gmail read/send (for Personal Assistant)
    - tasks: Google Tasks access (for Personal Assistant)
    
    Note: App must be "Published" (not Testing) for sensitive scopes to work.
    Users will see "This app isn't verified" warning - click Advanced → Go to app.
    """
    
    SCOPES = [
        "openid",
        "email", 
        "profile",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/tasks",
    ]
    
    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
    
    def __init__(
        self,
        client_id: str = GOOGLE_CLIENT_ID,
        client_secret: str = GOOGLE_CLIENT_SECRET,
        redirect_uri: str = OAUTH_REDIRECT_URI,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
        if not self.client_id or not self.client_secret:
            logger.warning("Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
    
    @property
    def name(self) -> str:
        return "google"
    
    def get_authorization_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL."""
        client = AsyncOAuth2Client(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=" ".join(self.SCOPES),
        )
        
        url, _ = client.create_authorization_url(
            self.AUTHORIZATION_URL,
            state=state,
            access_type="offline",  # Request refresh token
            prompt="consent",  # Force consent screen to get refresh token
        )
        
        return url
    
    async def handle_callback(self, code: str) -> tuple[OAuthTokens, OAuthUserInfo]:
        """Exchange Google authorization code for tokens and user info."""
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        ) as client:
            # Exchange code for tokens
            token = await client.fetch_token(
                self.TOKEN_URL,
                code=code,
            )
            
            # Calculate expiration
            expires_at = None
            if "expires_in" in token:
                expires_at = datetime.utcnow() + timedelta(seconds=token["expires_in"])
            
            tokens = OAuthTokens(
                access_token=token["access_token"],
                refresh_token=token.get("refresh_token"),
                token_type=token.get("token_type", "Bearer"),
                expires_at=expires_at,
                scopes=token.get("scope", "").split(),
                id_token=token.get("id_token"),
            )
            
            # Fetch user info
            resp = await client.get(self.USERINFO_URL)
            user_data = resp.json()
            
            user_info = OAuthUserInfo(
                provider=self.name,
                provider_user_id=user_data.get("sub"),
                email=user_data.get("email"),
                name=user_data.get("name"),
                picture=user_data.get("picture"),
            )
            
            logger.info(f"Google OAuth successful for user: {user_info.email}")
            return tokens, user_info
    
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired Google access token."""
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
        ) as client:
            token = await client.refresh_token(
                self.TOKEN_URL,
                refresh_token=refresh_token,
            )
            
            expires_at = None
            if "expires_in" in token:
                expires_at = datetime.utcnow() + timedelta(seconds=token["expires_in"])
            
            return OAuthTokens(
                access_token=token["access_token"],
                refresh_token=token.get("refresh_token", refresh_token),  # Keep old if not provided
                token_type=token.get("token_type", "Bearer"),
                expires_at=expires_at,
                scopes=token.get("scope", "").split(),
            )


# =============================================================================
# OAuth Provider Factory
# =============================================================================

_providers: Dict[str, OAuthProvider] = {}

def get_oauth_provider(name: str) -> OAuthProvider:
    """Get OAuth provider by name (factory pattern)."""
    if name not in _providers:
        if name == "google":
            _providers[name] = GoogleOAuthProvider()
        else:
            raise ValueError(f"Unknown OAuth provider: {name}")
    return _providers[name]


def get_available_providers() -> list[str]:
    """Get list of available OAuth provider names."""
    providers = []
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        providers.append("google")
    return providers


# =============================================================================
# Database Operations for OAuth Tokens
# =============================================================================

async def ensure_oauth_tables():
    """Create OAuth tokens table if it doesn't exist."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS user_oauth_tokens (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider VARCHAR(50) NOT NULL,
        access_token TEXT NOT NULL,
        refresh_token TEXT,
        token_expires_at TIMESTAMP WITH TIME ZONE,
        scopes TEXT[],
        provider_user_id VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, provider)
    );
    """
    
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set, skipping OAuth table creation")
        return
    
    try:
        async with await AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute(create_table_query)
            await conn.commit()
            logger.info("OAuth tokens table ensured.")
    except Exception as e:
        logger.error(f"Failed to create OAuth tables: {e}")


async def save_oauth_tokens(
    user_id: str,
    provider: str,
    tokens: OAuthTokens,
    provider_user_id: Optional[str] = None,
) -> None:
    """Save or update OAuth tokens for a user."""
    query = """
    INSERT INTO user_oauth_tokens (id, user_id, provider, access_token, refresh_token, 
                                   token_expires_at, scopes, provider_user_id, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (user_id, provider) DO UPDATE SET
        access_token = EXCLUDED.access_token,
        refresh_token = COALESCE(EXCLUDED.refresh_token, user_oauth_tokens.refresh_token),
        token_expires_at = EXCLUDED.token_expires_at,
        scopes = EXCLUDED.scopes,
        provider_user_id = EXCLUDED.provider_user_id,
        updated_at = NOW()
    """
    
    async with await AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, (
                uuid.uuid4(),
                uuid.UUID(user_id),
                provider,
                tokens.access_token,
                tokens.refresh_token,
                tokens.expires_at,
                tokens.scopes,
                provider_user_id,
            ))
        await conn.commit()
        logger.info(f"Saved OAuth tokens for user {user_id}, provider {provider}")


async def get_oauth_tokens(user_id: str, provider: str) -> Optional[OAuthTokens]:
    """Get OAuth tokens for a user and provider."""
    query = """
    SELECT access_token, refresh_token, token_expires_at, scopes
    FROM user_oauth_tokens
    WHERE user_id = %s AND provider = %s
    """
    
    async with await AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, (uuid.UUID(user_id), provider))
            row = await cur.fetchone()
            
            if not row:
                return None
            
            return OAuthTokens(
                access_token=row[0],
                refresh_token=row[1],
                token_type="Bearer",
                expires_at=row[2],
                scopes=row[3] or [],
            )


async def delete_oauth_tokens(user_id: str, provider: str) -> bool:
    """Delete OAuth tokens for a user and provider."""
    query = "DELETE FROM user_oauth_tokens WHERE user_id = %s AND provider = %s"
    
    async with await AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, (uuid.UUID(user_id), provider))
            deleted = cur.rowcount > 0
        await conn.commit()
        return deleted


async def get_valid_access_token(user_id: str, provider: str) -> Optional[str]:
    """
    Get a valid access token, refreshing if necessary.
    
    This is the main function services should use to get tokens.
    """
    tokens = await get_oauth_tokens(user_id, provider)
    if not tokens:
        return None
    
    # Check if token is expired or about to expire (5 min buffer)
    if tokens.expires_at:
        buffer = timedelta(minutes=5)
        if datetime.utcnow() + buffer >= tokens.expires_at:
            # Token expired, try to refresh
            if tokens.refresh_token:
                try:
                    oauth_provider = get_oauth_provider(provider)
                    new_tokens = await oauth_provider.refresh_access_token(tokens.refresh_token)
                    await save_oauth_tokens(user_id, provider, new_tokens)
                    return new_tokens.access_token
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    return None
            else:
                logger.warning(f"Token expired and no refresh token available for user {user_id}")
                return None
    
    return tokens.access_token
