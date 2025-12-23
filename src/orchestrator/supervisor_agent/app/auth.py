import os
import uuid
import logging
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field
import bcrypt
from psycopg import AsyncConnection
import jwt
from dotenv import load_dotenv

# Load .env file (for local development)
load_dotenv()

# Logger
logger = logging.getLogger("auth")

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
    """Create users table if it doesn't exist."""
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
        async with await AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute(create_table_query)
                
                # Add columns if they don't exist (simple migration)
                try:
                    await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255);")
                    await cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP WITH TIME ZONE;")
                except Exception as e:
                     logger.warning(f"Migration warning (columns might exist): {e}")

            await conn.commit()
            logger.info("Users table ensure check completed.")
    except Exception as e:
        logger.error(f"Failed to ensure users table: {e}")
        raise

async def create_user(user: UserRegisterRequest) -> UserResponse:
    """Register a new user."""
    user_id = uuid.uuid4()
    hashed_password = get_password_hash(user.password)
    
    query = """
    INSERT INTO users (id, email, password_hash, name, tenant_id)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id, email, name, tenant_id
    """
    
    async with await AsyncConnection.connect(DATABASE_URL) as conn:
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

async def authenticate_user(login_data: UserLoginRequest) -> Optional[UserResponse]:
    """Authenticate user credentials."""
    query = "SELECT id, email, name, tenant_id, password_hash FROM users WHERE email = %s"
    
    async with await AsyncConnection.connect(DATABASE_URL) as conn:
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
