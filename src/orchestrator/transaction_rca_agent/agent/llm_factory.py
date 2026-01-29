"""
LLM Factory for Transaction RCA Agent.

Factory for creating LLM instances with support for Gemini models.
"""

import os
import logging
from langchain_community.chat_models import ChatLiteLLM

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating LLM instances.
    Supports switching between providers via environment variables (e.g. Gemini, OpenRouter, Groq).
    Relies on LiteLLM's model string parsing (e.g. 'gemini/model', 'groq/model', 'openrouter/model').
    """

    @staticmethod
    def get_llm(
        model_env_var: str, temperature: float = 0, max_tokens: int = None
    ) -> ChatLiteLLM:
        """
        Get an LLM instance based on the model name in the specified environment variable.
        """
        model_name = os.getenv(model_env_var)
        if not model_name:
            # Fallback or error - deciding to error to ensure configuration is explicit
            raise ValueError(
                f"Environment variable '{model_env_var}' is not set. Please configure the LLM model name."
            )

        logger.info(
            f"Initializing LLM with model: {model_name} from env var: {model_env_var}"
        )

        # ChatLiteLLM wrapper handles the underlying litellm calls.
        # Ensure your API keys (GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY) are set in the environment.
        llm = ChatLiteLLM(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs={
                "num_retries": 5,
                "timeout": 60,
            },
        )
        return llm
