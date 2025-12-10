"""
LiteLLM Adapter

Concrete implementation of LLMProvider using LiteLLM library.
LiteLLM provides a unified interface for 100+ LLM providers.

Supports: OpenAI, Gemini, Groq, Ollama, Azure, Anthropic, and more.
"""

import logging
from typing import Any

import litellm

from orchestrator.interfaces.llm_provider import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)


class LiteLLMAdapter(LLMProvider):
    """
    LiteLLM adapter implementing the LLMProvider interface.
    
    This adapter unified input/output formats across all LLM providers,
    preventing vendor lock-in and optimizing operational costs.
    
    Model names follow LiteLLM format: "provider/model_name"
    Examples:
        - "openai/gpt-4-turbo"
        - "groq/llama-3.1-70b-versatile"
        - "ollama/mistral"
        - "gemini/gemini-pro"
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout: float = 60.0,
    ):
        """
        Initialize the LiteLLM adapter.
        
        Args:
            model_name: Model identifier in "provider/model" format.
            api_key: Optional API key (defaults to environment variable).
            api_base: Optional API base URL for custom endpoints.
            timeout: Request timeout in seconds.
        """
        self._model_name = model_name
        self._timeout = timeout
        
        # Configure LiteLLM settings
        litellm.drop_params = True  # Drop unsupported params silently
        litellm.set_verbose = False
        
        # Set API key if provided (otherwise uses env vars)
        if api_key:
            self._set_api_key(model_name, api_key)
        
        if api_base:
            self._api_base = api_base
        else:
            self._api_base = None
            
        logger.info(f"Initialized LiteLLM adapter for model: {model_name}")
    
    def _set_api_key(self, model_name: str, api_key: str) -> None:
        """Set the API key for the provider."""
        provider = model_name.split("/")[0].lower()
        
        # Map provider to environment variable
        key_mapping = {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "azure": "AZURE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        
        import os
        env_var = key_mapping.get(provider)
        if env_var:
            os.environ[env_var] = api_key
    
    @property
    def model_name(self) -> str:
        """Return the name of the model being used."""
        return self._model_name
    
    @property
    def supports_streaming(self) -> bool:
        """Return whether this provider supports streaming responses."""
        # Most modern providers support streaming
        provider = self._model_name.split("/")[0].lower()
        non_streaming_providers = {"ollama"}  # Some local models may not support streaming
        return provider not in non_streaming_providers
    
    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate a response from the LLM using LiteLLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
            tools: Optional list of tool definitions for function calling.
            json_schema: Optional JSON schema for structured output.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens in response.
            
        Returns:
            The generated response text.
        """
        try:
            kwargs: dict[str, Any] = {
                "model": self._model_name,
                "messages": messages,
                "temperature": temperature,
                "timeout": self._timeout,
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            if tools:
                kwargs["tools"] = tools
            
            if json_schema:
                kwargs["response_format"] = {"type": "json_object"}
            
            if self._api_base:
                kwargs["api_base"] = self._api_base
            
            response = await litellm.acompletion(**kwargs)
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            logger.error(f"LiteLLM error for {self._model_name}: {e}")
            raise LLMProviderError(
                message=str(e),
                provider=self._model_name,
                original_error=e,
            )
    
    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Generate a response that may include tool calls.
        
        Args:
            messages: List of message dictionaries.
            tools: List of tool definitions.
            temperature: Sampling temperature.
            
        Returns:
            Dictionary containing 'content' and optionally 'tool_calls'.
        """
        try:
            kwargs: dict[str, Any] = {
                "model": self._model_name,
                "messages": messages,
                "tools": tools,
                "temperature": temperature,
                "timeout": self._timeout,
            }
            
            if self._api_base:
                kwargs["api_base"] = self._api_base
            
            response = await litellm.acompletion(**kwargs)
            message = response.choices[0].message
            
            result: dict[str, Any] = {
                "content": message.content or "",
            }
            
            if hasattr(message, "tool_calls") and message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"LiteLLM tool call error for {self._model_name}: {e}")
            raise LLMProviderError(
                message=str(e),
                provider=self._model_name,
                original_error=e,
            )
