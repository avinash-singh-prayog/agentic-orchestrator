import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.auth import oauth2_scheme, SECRET_KEY, ALGORITHM
from app.services.llm_config_service import LLMConfigService

import jwt
from jwt.exceptions import InvalidTokenError

logger = logging.getLogger("settings_router")

router = APIRouter(
    prefix="/supervisor-agent/settings",
    tags=["settings"]
)

# Service instance
_config_service = LLMConfigService()

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """Validate token and return user_id."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Models
class LLMConfigBase(BaseModel):
    provider: str
    model_name: str
    config_name: str = "Default Config"

class LLMConfigCreate(LLMConfigBase):
    api_key: Optional[str] = None # Optional only if reusing logic, but for create usually required or we can allow empty

class LLMConfigResponse(LLMConfigBase):
    id: str
    is_active: bool
    is_configured: bool # Has API key?

class LLMUpdateActive(BaseModel):
    pass # No body needed for simple activation

# -----------------------------------------------------------------------------
# New Endpoints for Multiple Configs
# -----------------------------------------------------------------------------

@router.get("/llm-configs", response_model=List[LLMConfigResponse])
async def list_configs(user_id: str = Depends(get_current_user_id)):
    """List all LLM configurations for the user."""
    return await _config_service.list_configs(user_id)

@router.post("/llm-configs", response_model=LLMConfigResponse)
async def create_config(
    config: LLMConfigCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new LLM configuration."""
    if not config.provider or not config.model_name:
         raise HTTPException(status_code=400, detail="Provider and Model Name are required")
    
    try:
        new_id = await _config_service.create_config(
            user_id, 
            config.provider, 
            config.model_name, 
            config.api_key or "",
            config.config_name
        )
        return {
            "id": new_id,
            "provider": config.provider,
            "model_name": config.model_name,
            "config_name": config.config_name,
            "is_active": True, # First one is active basically, or logic in service
            "is_configured": bool(config.api_key)
        }
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/llm-configs/{config_id}/activate")
async def activate_config(
    config_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Set a specific configuration as active."""
    try:
        success = await _config_service.activate_config(user_id, config_id)
        if not success:
            raise HTTPException(status_code=404, detail="Config not found")
        return {"status": "success", "message": "Configuration activated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/llm-configs/{config_id}")
async def delete_config(
    config_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a configuration."""
    try:
        await _config_service.delete_config(user_id, config_id)
        return {"status": "success"}
    except Exception as e:
         logger.error(f"Failed to delete config: {e}")
         raise HTTPException(status_code=500, detail="Internal server error")

# -----------------------------------------------------------------------------
# Backward Compatibility / Single Active Logic
# -----------------------------------------------------------------------------

@router.get("/llm-config")
async def get_active_llm_config(user_id: str = Depends(get_current_user_id)):
    """Get the currently active LLM configuration."""
    config = await _config_service.get_active_config(user_id)
    if not config:
        # Return default empty structure if nothing configured
        return {
            "provider": None,
            "model_name": None,
            "is_configured": False
        }
    
    return {
        "provider": config["provider"],
        "model_name": config["model_name"],
        "is_configured": bool(config.get("api_key"))
    }


@router.put("/llm-config")
async def update_llm_config(
    config: LLMConfigCreate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Legacy/Simple update:
    If no configs exist, creates one.
    If active config exists, updates it.
    """
    # Check for active config
    active = await _config_service.get_active_config(user_id)
    
    try:
        if active:
            # Update existing active
            await _config_service.update_config(
                user_id, 
                active["id"], 
                config.provider, 
                config.model_name, 
                config.api_key,
                config.config_name or active.get("config_name", "Default Config")
            )
        else:
            # Create new
            await _config_service.create_config(
                user_id, 
                config.provider, 
                config.model_name, 
                config.api_key or "",
                config.config_name
            )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
