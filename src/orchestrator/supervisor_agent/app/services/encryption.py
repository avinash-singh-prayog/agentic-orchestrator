import os
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger("encryption_service")

class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data using Fernet symmetric encryption.
    """
    
    def __init__(self):
        # In production, this key should come from a secure secret manager.
        # For this setup, we use a dedicated env var or fallback to the JWT secret hashed/encoded.
        self._key = self._get_key()
        self._fernet = Fernet(self._key)

    def _get_key(self) -> bytes:
        """Retrieve or generate a valid Fernet key."""
        key = os.getenv("ENCRYPTION_KEY")
        
        if key:
            try:
                # Validate key format
                return key.encode() if isinstance(key, str) else key
            except Exception:
                logger.warning("Invalid ENCRYPTION_KEY format. Generating temporary key.")
                
        # Fallback for dev: Use JWT_SECRET_KEY to seed a consistent key if possible, 
        # or just generate one (note: generating one means restart invalidates old keys).
        # For simplicity and persistence in dev without a dedicated key, we'll try to use JWT_SECRET
        # BUT Fernet requires a 32 url-safe base64-encoded bytes.
        
        jwt_secret = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-in-production")
        
        # Make it 32 chars url-safe base64. 
        # Ideally, the user should provide a valid Fernet key. 
        # We will generate a deterministic key from the secret for dev stability.
        import base64
        import hashlib
        
        # Hash to 32 bytes
        sha = hashlib.sha256(jwt_secret.encode()).digest()
        # Base64 encode to make it url-safe for Fernet
        return base64.urlsafe_b64encode(sha)

    def encrypt(self, plain_text: str) -> str:
        """Encrypt a string."""
        if not plain_text:
            return ""
        try:
            encrypted_bytes = self._fernet.encrypt(plain_text.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt a string."""
        if not encrypted_text:
            return ""
        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_text.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
