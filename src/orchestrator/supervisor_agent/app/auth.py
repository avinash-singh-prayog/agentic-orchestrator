import os
import uuid
import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pydantic import BaseModel, EmailStr, Field
import bcrypt
from psycopg import AsyncConnection, OperationalError, ProgrammingError
import jwt
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64

# Load .env file (for local development)
load_dotenv()

# Logger
logger = logging.getLogger("auth")

# Database connection timeout (seconds)
DB_CONNECTION_TIMEOUT = 10
DB_QUERY_TIMEOUT = 30


# ============================================================================
# Custom Exceptions
# ============================================================================

class DatabaseError(Exception):
    """Base exception for database errors."""
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class DatabaseConnectionError(DatabaseError):
    """Raised when unable to connect to the database."""
    pass

class DatabaseQueryError(DatabaseError):
    """Raised when a query fails."""
    pass

class DatabaseTimeoutError(DatabaseError):
    """Raised when a database operation times out."""
    pass

# JWT Config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Database URL - REQUIRED, no hardcoded fallback
_raw_db_url = os.getenv("DATABASE_URL")
if not _raw_db_url:
    raise ValueError("DATABASE_URL environment variable is required but not set")

# Strip quotes that may be accidentally included in ECS task definitions
DATABASE_URL = _raw_db_url.strip('"').strip("'")

# Log at startup for debugging (mask password)
_masked_url = DATABASE_URL.split('@')[0].rsplit(':', 1)[0] + ':***@' + DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL[:30]
logger.info(f"DATABASE_URL loaded: {_masked_url}")

# Hardcoded Tenant ID as per requirement
DEFAULT_TENANT_ID = "507f1f77bcf86cd799439011"

# ============================================================================
# Encryption Configuration
# ============================================================================

# Get or generate encryption key for API keys
_encryption_key_raw = os.getenv("ENCRYPTION_KEY")
if not _encryption_key_raw:
    # Generate a new key if not set (for development only)
    # In production, this MUST be set in environment
    logger.warning("ENCRYPTION_KEY not set, generating new key (NOT SAFE FOR PRODUCTION)")
    _encryption_key_raw = Fernet.generate_key().decode()
    logger.warning(f"Generated encryption key: {_encryption_key_raw}")

# Ensure the key is properly formatted for Fernet
try:
    # If it's a base64 string already, use it
    ENCRYPTION_KEY = _encryption_key_raw.encode() if isinstance(_encryption_key_raw, str) else _encryption_key_raw
    _cipher = Fernet(ENCRYPTION_KEY)
except Exception as e:
    # If the key is invalid, generate a new one
    logger.error(f"Invalid ENCRYPTION_KEY format: {e}. Generating new key.")
    ENCRYPTION_KEY = Fernet.generate_key()
    _cipher = Fernet(ENCRYPTION_KEY)
    logger.warning(f"Generated new encryption key: {ENCRYPTION_KEY.decode()}")

# ============================================================================
# Encryption Utilities
# ============================================================================

def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    if not api_key:
        return ""
    try:
        encrypted = _cipher.encrypt(api_key.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {e}")
        raise

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage."""
    if not encrypted_key:
        return ""
    try:
        decrypted = _cipher.decrypt(encrypted_key.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        raise

# ============================================================================
# Models
# ============================================================================

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserForgotPasswordRequest(BaseModel):
    email: EmailStr

class UserResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    tenant_id: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ============================================================================
# Utils
# ============================================================================

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ============================================================================
# DB Operations
# ============================================================================

async def ensure_users_table():
    """Create users table if it doesn't exist with proper error handling."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        name VARCHAR(255),
        tenant_id VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        llm_provider VARCHAR(50),
        llm_model VARCHAR(100),
        llm_api_key_encrypted TEXT,
        llm_config_updated_at TIMESTAMP WITH TIME ZONE
    );
    """
    try:
        async def _do_setup():
            try:
                async with await AsyncConnection.connect(
                    DATABASE_URL,
                    connect_timeout=DB_CONNECTION_TIMEOUT
                ) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(create_table_query)
                        
                        # Add columns if they don't exist (simple migration)
                        try:
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255);")
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP WITH TIME ZONE;")
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;")
                            # LLM configuration columns
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50);")
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100);")
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS llm_api_key_encrypted TEXT;")
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS llm_config_updated_at TIMESTAMP WITH TIME ZONE;")
                        except Exception as e:
                             logger.warning(f"Migration warning (columns might exist): {e}")

                    await conn.commit()
                    logger.info("Users table ensure check completed.")
            except OperationalError as e:
                logger.error(f"Database connection error during table setup: {e}")
                raise DatabaseConnectionError(
                    f"Unable to connect to database: {str(e)}",
                    original_error=e
                )
            except ProgrammingError as e:
                logger.error(f"Database query error during table setup: {e}")
                raise DatabaseQueryError(
                    f"Database query failed: {str(e)}",
                    original_error=e
                )
        
        await asyncio.wait_for(_do_setup(), timeout=DB_QUERY_TIMEOUT)
        
    except asyncio.TimeoutError:
        logger.error(f"Database table setup timed out after {DB_QUERY_TIMEOUT}s")
        raise DatabaseTimeoutError(
            f"Database operation timed out after {DB_QUERY_TIMEOUT} seconds"
        )
    except DatabaseError:
        raise
    except Exception as e:
        logger.error(f"Failed to ensure users table: {e}")
        raise

async def create_user(user: UserRegisterRequest) -> UserResponse:
    """Register a new user with proper error handling."""
    user_id = uuid.uuid4()
    hashed_password = get_password_hash(user.password)
    
    query = """
    INSERT INTO users (id, email, password_hash, name, tenant_id)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id, email, name, tenant_id
    """
    
    try:
        async def _do_create():
            try:
                async with await AsyncConnection.connect(
                    DATABASE_URL,
                    connect_timeout=DB_CONNECTION_TIMEOUT
                ) as conn:
                    async with conn.cursor() as cur:
                        # Check if user exists
                        await cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
                        if await cur.fetchone():
                            raise ValueError("User with this email already exists")
                        
                        await cur.execute(query, (
                            user_id, 
                            user.email, 
                            hashed_password, 
                            user.name or user.email.split('@')[0], 
                            DEFAULT_TENANT_ID
                        ))
                        row = await cur.fetchone()
                        await conn.commit()
                        
                        return UserResponse(
                            id=str(row[0]),
                            email=row[1],
                            name=row[2],
                            tenant_id=row[3]
                        )
            except OperationalError as e:
                logger.error(f"Database connection error during user creation: {e}")
                raise DatabaseConnectionError(
                    f"Unable to connect to database: {str(e)}",
                    original_error=e
                )
            except ProgrammingError as e:
                logger.error(f"Database query error during user creation: {e}")
                raise DatabaseQueryError(
                    f"Database query failed: {str(e)}",
                    original_error=e
                )
        
        return await asyncio.wait_for(_do_create(), timeout=DB_QUERY_TIMEOUT)
        
    except asyncio.TimeoutError:
        logger.error(f"User creation timed out after {DB_QUERY_TIMEOUT}s")
        raise DatabaseTimeoutError(
            f"Database operation timed out after {DB_QUERY_TIMEOUT} seconds"
        )
    except ValueError:
        # Re-raise ValueError for "user already exists"
        raise
    except DatabaseError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during user creation: {e}")
        import traceback
        traceback.print_exc()
        raise DatabaseError(f"User creation failed due to an unexpected error: {str(e)}", original_error=e)

async def get_or_create_google_user(email: str, name: str, google_id: str) -> UserResponse:
    """Get existing user or create new one from Google profile."""
    query_find = "SELECT id, email, name, tenant_id FROM users WHERE email = %s"
    
    # We set a random password for OAuth users so password_hash NOT NULL constraint is satisfied
    # and they can technically reset it later if they want to login via password.
    random_password = str(uuid.uuid4())
    hashed_password = get_password_hash(random_password)
    new_user_id = uuid.uuid4()
    
    insert_query = """
    INSERT INTO users (id, email, password_hash, name, tenant_id, google_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, email, name, tenant_id
    """
    
    update_google_id_query = "UPDATE users SET google_id = %s WHERE email = %s AND google_id IS NULL"

    try:
        async def _do_google_auth():
            try:
                async with await AsyncConnection.connect(
                    DATABASE_URL,
                    connect_timeout=DB_CONNECTION_TIMEOUT
                ) as conn:
                    async with conn.cursor() as cur:
                        # 1. Check if user exists
                        await cur.execute(query_find, (email,))
                        row = await cur.fetchone()
                        
                        if row:
                            # User exists
                            user_id_found, email_found, name_found, tenant_id_found = row
                            
                            # Optionally link google_id if missing
                            # We can do this safely.
                            await cur.execute(update_google_id_query, (google_id, email))
                            await conn.commit()
                            
                            return UserResponse(
                                id=str(user_id_found),
                                email=email_found,
                                name=name_found,
                                tenant_id=tenant_id_found
                            )
                        else:
                            # 2. Create new user
                            await cur.execute(insert_query, (
                                new_user_id,
                                email,
                                hashed_password,
                                name,
                                DEFAULT_TENANT_ID,
                                google_id
                            ))
                            row = await cur.fetchone()
                            await conn.commit()
                            
                            return UserResponse(
                                id=str(row[0]),
                                email=row[1],
                                name=row[2],
                                tenant_id=row[3]
                            )
                            
            except OperationalError as e:
                logger.error(f"Database connection error during google auth: {e}")
                raise DatabaseConnectionError(f"Unable to connect to database: {str(e)}", original_error=e)
            except ProgrammingError as e:
                logger.error(f"Database query error during google auth: {e}")
                raise DatabaseQueryError(f"Database query failed: {str(e)}", original_error=e)
        
        return await asyncio.wait_for(_do_google_auth(), timeout=DB_QUERY_TIMEOUT)
        
    except asyncio.TimeoutError:
        raise DatabaseTimeoutError(f"Database operation timed out after {DB_QUERY_TIMEOUT} seconds")
    except DatabaseError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during google auth: {e}")
        raise DatabaseError(f"Google auth failed: {str(e)}", original_error=e)

async def authenticate_user(login_data: UserLoginRequest) -> Optional[UserResponse]:
    """Authenticate user credentials with proper error handling."""
    query = "SELECT id, email, name, tenant_id, password_hash FROM users WHERE email = %s"
    
    try:
        # Wrap the entire operation with a timeout
        async def _do_auth():
            try:
                async with await AsyncConnection.connect(
                    DATABASE_URL,
                    connect_timeout=DB_CONNECTION_TIMEOUT
                ) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, (login_data.email,))
                        row = await cur.fetchone()
                        
                        if not row:
                            return None
                        
                        user_id, email, name, tenant_id, pwd_hash = row
                        
                        if not verify_password(login_data.password, pwd_hash):
                            return None
                        
                        return UserResponse(
                            id=str(user_id),
                            email=email,
                            name=name,
                            tenant_id=tenant_id
                        )
            except OperationalError as e:
                # Connection-level errors (host unreachable, auth failed, etc.)
                logger.error(f"Database connection error during login: {e}")
                raise DatabaseConnectionError(
                    f"Unable to connect to database: {str(e)}",
                    original_error=e
                )
            except ProgrammingError as e:
                # Query/syntax errors
                logger.error(f"Database query error during login: {e}")
                raise DatabaseQueryError(
                    f"Database query failed: {str(e)}",
                    original_error=e
                )
        
        # Apply overall timeout
        return await asyncio.wait_for(_do_auth(), timeout=DB_QUERY_TIMEOUT)
        
    except asyncio.TimeoutError:
        logger.error(f"Database operation timed out after {DB_QUERY_TIMEOUT}s")
        raise DatabaseTimeoutError(
            f"Database operation timed out after {DB_QUERY_TIMEOUT} seconds"
        )
    except DatabaseError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error during authentication: {e}")
        import traceback
        traceback.print_exc()
        raise DatabaseError(f"Authentication failed due to an unexpected error: {str(e)}", original_error=e)

async def create_password_reset_token(email: str) -> Optional[str]:
    """Generate a reset token and save it to DB."""
    token = str(uuid.uuid4())
    # Expires in 1 hour
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    async with await AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            # Check if user exists
            await cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if not await cur.fetchone():
                return None
            
            # Update user with token
            await cur.execute(
                "UPDATE users SET reset_token = %s, reset_token_expires_at = %s WHERE email = %s",
                (token, expires_at, email)
            )
            await conn.commit()
            
    # In a real app, send email here.
    # For now, we Log it.
    logger.info(f"PASSWORD RESET LINK: http://localhost:3000/reset-password?token={token}")
    return token

async def reset_password(token: str, new_password: str) -> bool:
    """Reset password using token."""
    hashed_password = get_password_hash(new_password)
    now = datetime.utcnow()
    
    async with await AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            # Find user with valid token
            await cur.execute(
                "SELECT id FROM users WHERE reset_token = %s AND reset_token_expires_at > %s",
                (token, now)
            )
            row = await cur.fetchone()
            
            if not row:
                return False
                
            # Update password and clear token
            await cur.execute(
                "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires_at = NULL WHERE id = %s",
                (hashed_password, row[0])
            )
            await conn.commit()
            
    return True

async def get_user_llm_config(user_id: str) -> Optional[dict]:
    """Get user's LLM configuration from database."""
    query = """
    SELECT llm_provider, llm_model, llm_api_key_encrypted, llm_config_updated_at
    FROM users
    WHERE id = %s
    """
    
    try:
        async def _do_get():
            try:
                async with await AsyncConnection.connect(
                    DATABASE_URL,
                    connect_timeout=DB_CONNECTION_TIMEOUT
                ) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, (user_id,))
                        row = await cur.fetchone()
                        
                        if not row:
                            return None
                        
                        provider, model, api_key_stored, updated_at = row
                        
                        # Log API key preview for debugging (first 10 + last 4 chars)
                        api_key_preview = ""
                        if api_key_stored:
                            api_key_preview = api_key_stored[:10] + "..." + api_key_stored[-4:] if len(api_key_stored) > 14 else "***"
                        
                        logger.info(f"Retrieved from DB for user {user_id}: provider={provider}, model={model}, has_api_key={bool(api_key_stored)}, api_key_length={len(api_key_stored) if api_key_stored else 0}, api_key_preview={api_key_preview}, updated_at={updated_at}")
                        
                        if not provider or not model:
                            logger.warning(f"Provider or model missing for user {user_id}")
                            return None
                        
                        # API key is stored directly (no encryption/decryption)
                        api_key = api_key_stored if api_key_stored else ""
                        
                        # Log the actual API key being returned (masked)
                        returned_preview = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
                        logger.info(f"Returning config for user {user_id}: provider={provider}, model={model}, has_api_key={bool(api_key)}, api_key_preview={returned_preview}")
                        
                        return {
                            "provider": provider,
                            "model": model,
                            "api_key": api_key,
                            "has_encrypted_key": bool(api_key_stored),  # Indicate if API key exists in DB
                            "updated_at": updated_at.isoformat() if updated_at else None
                        }
            except OperationalError as e:
                logger.error(f"Database connection error during LLM config fetch: {e}")
                raise DatabaseConnectionError(
                    f"Unable to connect to database: {str(e)}",
                    original_error=e
                )
            except ProgrammingError as e:
                logger.error(f"Database query error during LLM config fetch: {e}")
                raise DatabaseQueryError(
                    f"Database query failed: {str(e)}",
                    original_error=e
                )
        
        return await asyncio.wait_for(_do_get(), timeout=DB_QUERY_TIMEOUT)
        
    except asyncio.TimeoutError:
        logger.error(f"Database operation timed out after {DB_QUERY_TIMEOUT}s")
        raise DatabaseTimeoutError(
            f"Database operation timed out after {DB_QUERY_TIMEOUT} seconds"
        )
    except DatabaseError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during LLM config fetch: {e}")
        raise DatabaseError(f"LLM config fetch failed: {str(e)}", original_error=e)

async def update_user_llm_config(user_id: str, provider: str, model: str, api_key: str) -> bool:
    """Update user's LLM configuration in database."""
    now = datetime.utcnow()
    
    logger.info(f"update_user_llm_config called: user_id={user_id}, provider={provider}, model={model}, api_key_provided={bool(api_key)}, api_key_length={len(api_key) if api_key else 0}")
    
    # If API key is provided, store it directly (no encryption) and update all fields
    # Otherwise, only update provider and model, keeping existing API key
    if api_key:
        # Store API key directly without encryption
        query = """
        UPDATE users
        SET llm_provider = %s, llm_model = %s, llm_api_key_encrypted = %s, llm_config_updated_at = %s
        WHERE id = %s
        """
        query_params = (provider, model, api_key, now, user_id)
        logger.info(f"Updating all fields including API key for user {user_id}")
    else:
        # Only update provider and model, keep existing API key
        query = """
        UPDATE users
        SET llm_provider = %s, llm_model = %s, llm_config_updated_at = %s
        WHERE id = %s
        """
        query_params = (provider, model, now, user_id)
        logger.info(f"Updating only provider and model (keeping existing API key) for user {user_id}")
    
    try:
        async def _do_update():
            try:
                async with await AsyncConnection.connect(
                    DATABASE_URL,
                    connect_timeout=DB_CONNECTION_TIMEOUT
                ) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, query_params)
                        rows_affected = cur.rowcount
                        await conn.commit()
                        logger.info(f"Database update completed for user {user_id}, rows affected: {rows_affected}")
                        return True
            except OperationalError as e:
                logger.error(f"Database connection error during LLM config update: {e}")
                raise DatabaseConnectionError(
                    f"Unable to connect to database: {str(e)}",
                    original_error=e
                )
            except ProgrammingError as e:
                logger.error(f"Database query error during LLM config update: {e}")
                raise DatabaseQueryError(
                    f"Database query failed: {str(e)}",
                    original_error=e
                )
        
        return await asyncio.wait_for(_do_update(), timeout=DB_QUERY_TIMEOUT)
        
    except asyncio.TimeoutError:
        logger.error(f"Database operation timed out after {DB_QUERY_TIMEOUT}s")
        raise DatabaseTimeoutError(
            f"Database operation timed out after {DB_QUERY_TIMEOUT} seconds"
        )
    except DatabaseError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during LLM config update: {e}")
        raise DatabaseError(f"LLM config update failed: {str(e)}", original_error=e)
