import os
import logging
from langchain_community.chat_models import ChatLiteLLM
from typing import Optional, Dict

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
            
            # Set API key in environment temporarily (LiteLLM reads from env)
            env_var_map = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "google": "GEMINI_API_KEY",
                "groq": "GROQ_API_KEY",
                "openrouter": "OPENROUTER_API_KEY"
            }
            
            env_var = env_var_map.get(provider)
            original_key = None
            
            try:
                if env_var and api_key:
                    # Save original value
                    original_key = os.environ.get(env_var)
                    # Set temporary API key
                    os.environ[env_var] = api_key
                    logger.debug(f"Set {env_var} for user-configured LLM")
                
                model_kwargs = {
                    "num_retries": 5,
                    "timeout": 60,
                }
                
                llm = ChatLiteLLM(
                    model=model_string,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_kwargs=model_kwargs
                )
                
                return llm
            except Exception as e:
                # Restore original key on error
                if env_var and original_key:
                    os.environ[env_var] = original_key
                elif env_var and env_var in os.environ:
                    del os.environ[env_var]
                raise
        
        # Fallback to environment variables (backward compatibility)
        # If vision is needed, check for vision-specific model first
        if use_vision:
            vision_model = os.getenv("SUPERVISOR_VISION_LLM")
            if vision_model:
                model_name = vision_model
                logger.info(f"Using vision model: {model_name} from SUPERVISOR_VISION_LLM")
            else:
                # Fallback to regular model (may or may not support vision)
                if not model_env_var:
                    raise ValueError("model_env_var is required when user_config is not provided")
                model_name = os.getenv(model_env_var)
                if model_name:
                    logger.info(f"Using model: {model_name} for vision (no SUPERVISOR_VISION_LLM set)")
                else:
                    raise ValueError(f"Environment variable '{model_env_var}' is not set. Please configure the LLM model name.")
        else:
            if not model_env_var:
                raise ValueError("model_env_var is required when user_config is not provided")
            model_name = os.getenv(model_env_var)
            if not model_name:
                # Fallback or error - deciding to error to ensure configuration is explicit
                raise ValueError(f"Environment variable '{model_env_var}' is not set. Please configure the LLM model name.")
            logger.info(f"Initializing LLM with model: {model_name} from env var: {model_env_var}")

        # Determine which API key to use based on the model provider
        model_kwargs = {
            "num_retries": 5,
            "timeout": 60,
        }
        
        # ChatLiteLLM wrapper handles the underlying litellm calls.
        # Pass API key via model_kwargs to ensure authentication works
        llm = ChatLiteLLM(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs=model_kwargs
        )
        return llm
