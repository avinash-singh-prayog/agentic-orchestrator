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
from fastapi.security import OAuth2PasswordBearer

# Load .env file (for local development)
load_dotenv()

# Logger
logger = logging.getLogger("auth")

# Database connection timeout (seconds)
DB_CONNECTION_TIMEOUT = 10
DB_QUERY_TIMEOUT = 30

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/supervisor-agent/auth/login")


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
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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

                        # Create user_llm_configs table
                        # Note: user_id is NOT unique anymore to allow multiple configs
                        create_config_table_query = """
                        CREATE TABLE IF NOT EXISTS user_llm_configs (
                            id UUID PRIMARY KEY,
                            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            config_name VARCHAR(100) DEFAULT 'Default Config',
                            provider VARCHAR(50) NOT NULL,
                            model_name VARCHAR(100) NOT NULL,
                            api_key_encrypted TEXT,
                            is_active BOOLEAN DEFAULT FALSE,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        """
                        await cur.execute(create_config_table_query)
                        
                        # Migrations for existing tables
                        try:
                            # 1. Drop UNIQUE constraint on user_id if it exists (from previous version)
                            # We suspect standard naming 'user_llm_configs_user_id_key'
                            await cur.execute("""
                                DO $$
                                BEGIN
                                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_llm_configs_user_id_key') THEN
                                        ALTER TABLE user_llm_configs DROP CONSTRAINT user_llm_configs_user_id_key;
                                    END IF;
                                END $$;
                            """)
                            
                            # 2. Add new columns
                            await cur.execute("ALTER TABLE user_llm_configs ADD COLUMN IF NOT EXISTS config_name VARCHAR(100) DEFAULT 'Default Config';")
                            await cur.execute("ALTER TABLE user_llm_configs ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;") 
                            # Note: default TRUE for existing usage is good, but for multiple new ones we want careful logic. 
                            # For migration of EXISTING single row, TRUE is correct.
                            
                        except Exception as e:
                             logger.warning(f"Migration warning (user_llm_configs): {e}")

                        # Add columns if they don't exist (simple migration)
                        
                        # Add columns if they don't exist (simple migration)
                        try:
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255);")
                            await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP WITH TIME ZONE;")
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
