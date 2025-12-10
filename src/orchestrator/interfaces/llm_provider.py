"""
LLM Provider Interface

Abstract base class for LLM providers following the Dependency Inversion Principle.
This allows the orchestrator to work with any LLM provider that implements this interface.

Supports: OpenAI, Gemini, Groq, Ollama (via LiteLLM adapter)
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Adheres to Dependency Inversion Principle: High-level modules (agents)
    depend on this abstraction, not on concrete implementations.
    
    Follows Liskov Substitution Principle: Any provider implementation
    can substitute another without breaking the application logic.
    """
    
    @abstractmethod
    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
            tools: Optional list of tool definitions for function calling.
            json_schema: Optional JSON schema for structured output.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens in response.
            
        Returns:
            The generated response text.
            
        Raises:
            LLMProviderError: If the LLM call fails.
        """
        pass
    
    @abstractmethod
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
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the model being used."""
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Return whether this provider supports streaming responses."""
        pass


class LLMProviderError(Exception):
    """Exception raised when an LLM provider operation fails."""
    
    def __init__(self, message: str, provider: str, original_error: Exception | None = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")
