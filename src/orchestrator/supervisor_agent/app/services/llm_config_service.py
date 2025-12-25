import logging
import uuid
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from psycopg import AsyncConnection, OperationalError, ProgrammingError

# Import directly from the file we just created
from app.services.encryption import EncryptionService
from app.auth import DATABASE_URL, DB_CONNECTION_TIMEOUT, DB_QUERY_TIMEOUT, DatabaseError, DatabaseQueryError

logger = logging.getLogger("llm_config_service")

class LLMConfigService:
    """
    Service to manage User LLM Configurations.
    Handles encryption/decryption of API keys transparently.
    Supports multiple configs per user.
    """
    
    def __init__(self):
        self._encryption = EncryptionService()

    async def get_active_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the ACTIVE LLM configuration for a user.
        Returns None if no active config found.
        """
        query = """
        SELECT id, provider, model_name, api_key_encrypted, config_name
        FROM user_llm_configs
        WHERE user_id = %s AND is_active = TRUE
        LIMIT 1
        """
        
        try:
            async with await AsyncConnection.connect(DATABASE_URL, connect_timeout=DB_CONNECTION_TIMEOUT) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (user_id,))
                    row = await cur.fetchone()
                    
                    if not row:
                        return None
                    
                    id_, provider, model_name, encrypted_key, config_name = row
                    
                    try:
                        api_key = self._encryption.decrypt(encrypted_key) if encrypted_key else None
                    except Exception as e:
                        logger.error(f"Failed to decrypt API key for user {user_id}: {e}")
                        api_key = None
                        
                    return {
                        "id": str(id_),
                        "config_name": config_name,
                        "provider": provider,
                        "model_name": model_name,
                        "api_key": api_key
                    }
        except Exception as e:
            logger.error(f"Error fetching active LLM config for user {user_id}: {e}")
            raise DatabaseError(f"Failed to fetch active LLM config: {e}")
            
    # Alias for backward compatibility if needed, but we should update usage
    async def get_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_active_config(user_id)

    async def list_configs(self, user_id: str) -> List[Dict[str, Any]]:
        """List all configs for a user."""
        query = """
        SELECT id, provider, model_name, config_name, is_active, api_key_encrypted
        FROM user_llm_configs
        WHERE user_id = %s
        ORDER BY updated_at DESC
        """
        try:
            async with await AsyncConnection.connect(DATABASE_URL, connect_timeout=DB_CONNECTION_TIMEOUT) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (user_id,))
                    rows = await cur.fetchall()
                    
                    results = []
                    for row in rows:
                        id_, provider, model_name, config_name, is_active, encrypted_key = row
                        # Check "configured" status by presence of encrypted key
                        is_configured = bool(encrypted_key)
                        
                        results.append({
                            "id": str(id_),
                            "config_name": config_name or f"{provider}/{model_name}",
                            "provider": provider,
                            "model_name": model_name,
                            "is_active": is_active,
                            "is_configured": is_configured
                        })
                    return results
        except Exception as e:
            logger.error(f"Error listing LLM configs for user {user_id}: {e}")
            raise DatabaseError(f"Failed to list LLM configs: {e}")

    async def create_config(self, user_id: str, provider: str, model_name: str, api_key: str, config_name: str) -> str:
        """Create a new LLM configuration."""
        encrypted_key = self._encryption.encrypt(api_key) if api_key else None
        new_id = uuid.uuid4()
        
        # Check if this is the first config; if so, make it active
        check_query = "SELECT 1 FROM user_llm_configs WHERE user_id = %s LIMIT 1"
        insert_query = """
        INSERT INTO user_llm_configs (id, user_id, provider, model_name, api_key_encrypted, config_name, is_active, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """
        
        try:
            async with await AsyncConnection.connect(DATABASE_URL, connect_timeout=DB_CONNECTION_TIMEOUT) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(check_query, (user_id,))
                    is_first = (await cur.fetchone()) is None
                    is_active = is_first
                    
                    await cur.execute(insert_query, (
                        new_id,
                        user_id,
                        provider,
                        model_name,
                        encrypted_key,
                        config_name,
                        is_active
                    ))
                    await conn.commit()
            return str(new_id)
        except Exception as e:
            logger.error(f"Error creating LLM config for user {user_id}: {e}")
            raise DatabaseError(f"Failed to create LLM config: {e}")

    async def activate_config(self, user_id: str, config_id: str) -> bool:
        """Set a specific config as active, deactivate others."""
        try:
            async with await AsyncConnection.connect(DATABASE_URL, connect_timeout=DB_CONNECTION_TIMEOUT) as conn:
                async with conn.cursor() as cur:
                    # Deactivate all
                    await cur.execute("UPDATE user_llm_configs SET is_active = FALSE WHERE user_id = %s", (user_id,))
                    # Activate specific
                    await cur.execute("UPDATE user_llm_configs SET is_active = TRUE WHERE user_id = %s AND id = %s", (user_id, config_id))
                    await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error activating LLM config {config_id}: {e}")
            raise DatabaseError(f"Failed to activate LLM config: {e}")

    async def delete_config(self, user_id: str, config_id: str) -> bool:
        """Delete specific config."""
        query = "DELETE FROM user_llm_configs WHERE user_id = %s AND id = %s"
        try:
            async with await AsyncConnection.connect(DATABASE_URL, connect_timeout=DB_CONNECTION_TIMEOUT) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (user_id, config_id))
                    await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting LLM config {config_id}: {e}")
            raise DatabaseError(f"Failed to delete LLM config: {e}")
            
    # For backward compatibility with simpler `update` logic if needed, 
    # but we should move API to use create/delete basically.
    # Or implement `update_config` for specific ID.
    async def update_config(self, user_id: str, config_id: str, provider: str, model_name: str, api_key: str, config_name: str) -> bool:
         """Update existing config."""
         # Logic similar to create but Update
         encrypted_key = self._encryption.encrypt(api_key) if api_key else None
         
         query = """
         UPDATE user_llm_configs 
         SET provider = %s, model_name = %s, config_name = %s, updated_at = CURRENT_TIMESTAMP
         WHERE user_id = %s AND id = %s
         """
         params = [provider, model_name, config_name, user_id, config_id]
         
         if encrypted_key:
             query = """
             UPDATE user_llm_configs 
             SET provider = %s, model_name = %s, config_name = %s, api_key_encrypted = %s, updated_at = CURRENT_TIMESTAMP
             WHERE user_id = %s AND id = %s
             """
             params = [provider, model_name, config_name, encrypted_key, user_id, config_id]

         try:
            async with await AsyncConnection.connect(DATABASE_URL, connect_timeout=DB_CONNECTION_TIMEOUT) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, tuple(params))
                    await conn.commit()
            return True
         except Exception as e:
            logger.error(f"Error updating LLM config {config_id}: {e}")
            raise DatabaseError(f"Failed to update LLM config: {e}")

