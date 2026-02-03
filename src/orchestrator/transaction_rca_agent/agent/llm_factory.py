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
                
                llm = ChatLiteLLM(
                    model=model_string,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_kwargs={
                        "num_retries": 5,
                        "timeout": 60,
                    },
                )
                return llm
            except Exception as e:
                # Restore original key on error
                if env_var and original_key:
                    os.environ[env_var] = original_key
                elif env_var and env_var in os.environ:
                    del os.environ[env_var]
                raise
        
        # No fallback to environment variables - user_config is required
        raise ValueError(
            "LLM configuration is required. Please provide user_config with provider, model, and api_key. "
            "Environment variable fallback has been removed. Users must configure their API key in the frontend."
        )
