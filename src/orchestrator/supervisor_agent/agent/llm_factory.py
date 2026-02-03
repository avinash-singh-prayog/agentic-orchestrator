import os
import logging
from langchain_community.chat_models import ChatLiteLLM
from typing import Optional, Dict
import litellm

logger = logging.getLogger(__name__)

class LLMFactory:
    """
    Factory for creating LLM instances.
    Supports switching between providers via environment variables (e.g. OpenRouter, Groq).
    Relies on LiteLLM's model string parsing (e.g. 'groq/model', 'openrouter/model').
    Supports vision models for image analysis.
    Supports user-provided configuration (provider, model, API key).
    """

    @staticmethod
    def get_llm(
        model_env_var: str = None,
        temperature: float = 0,
        max_tokens: int = None,
        use_vision: bool = False,
        user_config: Optional[Dict[str, str]] = None
    ) -> ChatLiteLLM:
        """
        Get an LLM instance based on the model name in the specified environment variable or user config.
        
        Args:
            model_env_var: Environment variable name containing the model identifier (fallback if user_config not provided)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            use_vision: If True, try to use a vision-capable model (checks SUPERVISOR_VISION_LLM env var first)
            user_config: Optional dict with {"provider": "openai", "model": "gpt-4", "api_key": "sk-..."}
                        If provided, this takes priority over environment variables
        
        Returns:
            ChatLiteLLM instance
        """
        # Priority: user_config > environment variables
        logger.info(f"LLMFactory.get_llm called with user_config: {user_config}, model_env_var: {model_env_var}, use_vision: {use_vision}")
        if user_config:
            logger.info(f"user_config type: {type(user_config)}, keys: {user_config.keys() if isinstance(user_config, dict) else 'not a dict'}, provider: {user_config.get('provider') if isinstance(user_config, dict) else None}, model: {user_config.get('model') if isinstance(user_config, dict) else None}")
        
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
            elif provider == "google":
                # Google Gemini models use "gemini/" prefix in LiteLLM
                if model.startswith("gemini/"):
                    model_string = model
                elif "/" in model:
                    # Already has provider prefix, use as-is
                    model_string = model
                else:
                    model_string = f"gemini/{model}"
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
            
            # CRITICAL FIX: Pass API key directly via model_kwargs instead of environment variable
            # This ensures the correct API key is used, especially for OpenRouter which may cache env vars
            # LiteLLM supports passing API keys via model_kwargs with provider-specific key names
            try:
                # Set reasonable default max_tokens if not provided to avoid exceeding account limits
                # Default 65535 is too high for free tier accounts
                effective_max_tokens = max_tokens if max_tokens is not None else 4000
                if max_tokens is None:
                    logger.info(f"max_tokens not specified, using default: {effective_max_tokens} (to avoid exceeding account limits)")
                
                # Build model_kwargs with API key passed directly
                # LiteLLM reads API keys from model_kwargs with provider-specific names
                model_kwargs = {
                    "num_retries": 5,
                    "timeout": 60,
                }
                
                # CRITICAL: For OpenRouter, we need to ensure the API key is used correctly
                # LiteLLM may cache API keys, so we need to set it in multiple ways
                if provider == "openrouter":
                    # Set in environment (required for LiteLLM)
                    os.environ[env_var] = api_key
                    # Also set via litellm's set_verbose to ensure it's used
                    # And pass in model_kwargs
                    model_kwargs["api_key"] = api_key
                    model_kwargs["OPENROUTER_API_KEY"] = api_key
                    # Force LiteLLM to use this API key by setting it in the litellm module
                    litellm.openrouter_api_key = api_key
                    logger.info(f"Set OpenRouter API key in environment, model_kwargs, and litellm module. API key: {api_key_preview}")
                elif provider == "openai":
                    model_kwargs["api_key"] = api_key
                    model_kwargs["OPENAI_API_KEY"] = api_key
                    os.environ[env_var] = api_key
                    litellm.openai_api_key = api_key
                elif provider == "anthropic":
                    model_kwargs["api_key"] = api_key
                    model_kwargs["ANTHROPIC_API_KEY"] = api_key
                    os.environ[env_var] = api_key
                    litellm.anthropic_api_key = api_key
                elif provider == "google":
                    model_kwargs["api_key"] = api_key
                    model_kwargs["GEMINI_API_KEY"] = api_key
                    os.environ[env_var] = api_key
                    litellm.gemini_api_key = api_key
                elif provider == "groq":
                    model_kwargs["api_key"] = api_key
                    os.environ[env_var] = api_key
                    litellm.groq_api_key = api_key
                else:
                    # For other providers, just set in environment and model_kwargs
                    os.environ[env_var] = api_key
                    model_kwargs["api_key"] = api_key
                    model_kwargs[env_var] = api_key
                
                logger.info(f"Set {env_var} in environment, model_kwargs, and litellm module. API key: {api_key_preview}")
                
                # Create LLM instance - API key is set in multiple places to ensure it's used
                llm = ChatLiteLLM(
                    model=model_string,
                    temperature=temperature,
                    max_tokens=effective_max_tokens,
                    model_kwargs=model_kwargs
                )
                
                # Verify the environment variable is still set correctly after LLM creation
                verify_env_key = os.environ.get(env_var)
                if verify_env_key != api_key:
                    logger.error(f"CRITICAL: Environment variable {env_var} changed after LLM creation! Expected: {api_key_preview}, Got: {verify_env_key[:10] + '...' + verify_env_key[-4:] if verify_env_key and len(verify_env_key) > 14 else 'None'}")
                else:
                    logger.info(f"Verified {env_var} is still set correctly after LLM creation: {api_key_preview}")
                
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
