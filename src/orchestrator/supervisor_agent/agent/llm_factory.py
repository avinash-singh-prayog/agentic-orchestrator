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
    def get_llm(model_env_var: str, temperature: float = 0, max_tokens: int = None) -> ChatLiteLLM:
        """
        Get an LLM instance based on the model name in the specified environment variable.
        """
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
        
        if model_name.startswith("openrouter/"):
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is not set. Required for OpenRouter models.")
            # Ensure API key is set in environment for LiteLLM to pick up
            os.environ["OPENROUTER_API_KEY"] = api_key
            logger.info("OPENROUTER_API_KEY configured for LiteLLM (length: %d)", len(api_key))
        elif model_name.startswith("groq/"):
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY environment variable is not set. Required for Groq models.")
            # Set API key in environment for LiteLLM to pick up
            os.environ["GROQ_API_KEY"] = api_key
            logger.info("GROQ_API_KEY configured for LiteLLM")

        # ChatLiteLLM wrapper handles the underlying litellm calls.
        # Pass API key via model_kwargs to ensure authentication works
        llm = ChatLiteLLM(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs=model_kwargs
        )
        return llm
