import os
import logging
from langchain_community.chat_models import ChatLiteLLM

logger = logging.getLogger(__name__)

class LLMFactory:
    """
    Factory for creating LLM instances.
    Supports switching between providers via environment variables (e.g. OpenRouter, Groq).
    Relies on LiteLLM's model string parsing (e.g. 'groq/model', 'openrouter/model').
    """

    @staticmethod
    def get_llm(model_env_var: str, temperature: float = 0, max_tokens: int = None, llm_config: dict = None) -> ChatLiteLLM:
        """
        Get an LLM instance.
        If llm_config is provided, uses it (provider/model, api_key).
        Otherwise falls back to model name in the specified environment variable.
        """
        model_name = None
        api_key = None
        
        if llm_config:
            # Construct model string for LiteLLM e.g. "openai/gpt-4" or "anthropic/claude-3-opus"
            # If provider is "ollama", model might just be "llama3" -> "ollama/llama3"
            provider = llm_config.get("provider", "").lower()
            name = llm_config.get("model_name", "")
            api_key = llm_config.get("api_key")
            
            if provider and name:
                # Some providers like 'openai' or 'anthropic' need prefix.
                # If name already has slash, assume it's full name.
                if "/" in name:
                    model_name = name
                elif provider:
                     model_name = f"{provider}/{name}"
                else:
                    model_name = name
        
        # Fallback to env var
        if not model_name:
            model_name = os.getenv(model_env_var)
        
        if not model_name:
            raise ValueError(f"Model Configuration Missing: Environment variable '{model_env_var}' is not set and no user config provided.")

        logger.info(f"Initializing LLM with model: {model_name}" + (" (User Configured)" if llm_config else " (Env Var)"))

        # ChatLiteLLM wrapper handles the underlying litellm calls.
        llm_kwargs = {
            "model": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model_kwargs": {
                "num_retries": 5,
                "timeout": 60,
            }
        }
        
        # If API Key is provided explicitly (from user config), pass it.
        # LiteLLM/ChatLiteLLM usually looks for env vars. To pass explicit key, 
        # we might need to set it in env temporarily or pass via some specific param?
        # ChatLiteLLM docs say: api_key param.
        if api_key:
            llm_kwargs["api_key"] = api_key
            
        llm = ChatLiteLLM(**llm_kwargs)
        return llm
