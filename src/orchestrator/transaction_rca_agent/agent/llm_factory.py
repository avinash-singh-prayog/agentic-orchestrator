"""
LLM Factory for Transaction RCA Agent.

Factory for creating LLM instances with support for Gemini models.
"""

import os
import logging
from langchain_community.chat_models import ChatLiteLLM
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating LLM instances.
    Supports switching between providers via environment variables (e.g. Gemini, OpenRouter, Groq).
    Relies on LiteLLM's model string parsing (e.g. 'gemini/model', 'groq/model', 'openrouter/model').
    Supports user-provided configuration (provider, model, API key).
    """

    @staticmethod
    def get_llm(
        model_env_var: str = None,
        temperature: float = 0,
        max_tokens: int = None,
        user_config: Optional[Dict[str, str]] = None
    ) -> ChatLiteLLM:
        """
        Get an LLM instance based on the model name in the specified environment variable or user config.
        
        Args:
            model_env_var: Environment variable name containing the model identifier (fallback if user_config not provided)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            user_config: Optional dict with {"provider": "openai", "model": "gpt-4", "api_key": "sk-..."}
                        If provided, this takes priority over environment variables
        
        Returns:
            ChatLiteLLM instance
        """
        # Priority: user_config > environment variables
        if user_config and user_config.get("provider") and user_config.get("model"):
            provider = user_config["provider"]
            model = user_config["model"]
            api_key = user_config.get("api_key", "")
            
            # Construct LiteLLM model string
            if provider == "openrouter":
                # OpenRouter models must always have openrouter/ prefix
                # Even if model has slash (e.g., "google/gemini-2.5-flash"), we need "openrouter/google/gemini-2.5-flash"
                if model.startswith("openrouter/"):
                    model_string = model
                else:
                    model_string = f"openrouter/{model}"
            elif provider == "groq":
                # Groq models may need meta-llama/ prefix for certain models
                # If model already has meta-llama/ prefix, use as-is
                if model.startswith("meta-llama/"):
                    model_string = f"groq/{model}"
                elif "/" in model:
                    # Already has some prefix, use as-is with groq/ prefix
                    model_string = f"groq/{model}"
                else:
                    # For llama-4 models, add meta-llama/ prefix
                    if model.startswith("llama-4"):
                        model_string = f"groq/meta-llama/{model}"
                    else:
                        model_string = f"groq/{model}"
            else:
                model_string = f"{provider}/{model}"
            
            logger.info(f"Initializing LLM with user config: {model_string} (provider: {provider})")
            
            # Validate API key is provided
            if not api_key or not api_key.strip():
                raise ValueError(f"API key is required for provider {provider} but was not provided in user_config")
            
            # Log API key info (masked for security)
            api_key_preview = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
            logger.info(f"Using user-provided API key: {api_key_preview} (length: {len(api_key)}) for provider {provider}")
            
            # Map provider to environment variable name
            env_var_map = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "google": "GEMINI_API_KEY",
                "groq": "GROQ_API_KEY",
                "openrouter": "OPENROUTER_API_KEY"
            }
            
            env_var = env_var_map.get(provider)
            if not env_var:
                raise ValueError(f"Unknown provider: {provider}. Cannot set API key.")
            
            # CRITICAL: Save original value and set user's API key
            # This ensures the user's API key is used, not the one from docker-compose/env
            original_key = os.environ.get(env_var)
            if original_key:
                original_preview = original_key[:10] + "..." + original_key[-4:] if len(original_key) > 14 else "***"
                logger.warning(f"Overriding existing {env_var} (original: {original_preview}) with user-provided key: {api_key_preview}")
            else:
                logger.info(f"Setting {env_var} with user-provided API key (no existing key found)")
            
            # Set the user's API key in environment (LiteLLM reads from env)
            os.environ[env_var] = api_key
            
            # Verify it was set correctly
            verify_key = os.environ.get(env_var)
            if verify_key != api_key:
                logger.error(f"CRITICAL: Failed to set {env_var}! Expected: {api_key_preview}, Got: {verify_key[:10] + '...' + verify_key[-4:] if verify_key and len(verify_key) > 14 else 'None'}")
                raise ValueError(f"Failed to set API key in environment variable {env_var}")
            
            logger.info(f"Successfully set {env_var} to user-provided API key. Verified: {api_key_preview}")
            
            try:
                # Set reasonable default max_tokens if not provided to avoid exceeding account limits
                # Default 65535 is too high for free tier accounts
                effective_max_tokens = max_tokens if max_tokens is not None else 4000
                if max_tokens is None:
                    logger.info(f"max_tokens not specified, using default: {effective_max_tokens} (to avoid exceeding account limits)")
                
                llm = ChatLiteLLM(
                    model=model_string,
                    temperature=temperature,
                    max_tokens=effective_max_tokens,
                    model_kwargs={
                        "num_retries": 5,
                        "timeout": 60,
                    },
                )
                logger.info(f"Successfully created LLM instance with user-provided API key for {provider}/{model}")
                return llm
            except Exception as e:
                logger.error(f"Failed to create LLM instance with user-provided API key: {e}", exc_info=True)
                # Restore original key on error
                if original_key:
                    os.environ[env_var] = original_key
                    logger.info(f"Restored original {env_var}")
                elif env_var in os.environ:
                    del os.environ[env_var]
                    logger.info(f"Removed {env_var} from environment")
                raise
        
        # No fallback to environment variables - user_config is required
        raise ValueError(
            "LLM configuration is required. Please provide user_config with provider, model, and api_key. "
            "Environment variable fallback has been removed. Users must configure their API key in the frontend."
        )
