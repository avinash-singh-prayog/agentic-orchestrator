"""
LLM Provider Factory

Factory function for creating LLM provider instances based on configuration.
This provides a clean separation between configuration and instantiation.
"""

from functools import lru_cache

from orchestrator.common.config import settings
from orchestrator.interfaces.llm_provider import LLMProvider
from orchestrator.providers.litellm_adapter import LiteLLMAdapter


def get_llm_provider(
    model_name: str | None = None,
    agent_type: str | None = None,
) -> LLMProvider:
    """
    Get an LLM provider instance.
    
    Args:
        model_name: Explicit model name (e.g., "openai/gpt-4-turbo").
                   If not provided, uses agent_type to determine model.
        agent_type: Agent type to get configured model for.
                   Options: "supervisor", "rate", "serviceability", "carrier"
    
    Returns:
        LLMProvider instance configured for the specified model.
        
    Example:
        # Get provider for supervisor agent
        provider = get_llm_provider(agent_type="supervisor")
        
        # Get provider for specific model
        provider = get_llm_provider(model_name="groq/llama-3.1-70b-versatile")
    """
    if model_name is None and agent_type is None:
        model_name = settings.supervisor_llm
    elif model_name is None:
        # Map agent type to configured model
        agent_models = {
            "supervisor": settings.supervisor_llm,
            "rate": settings.rate_agent_llm,
            "serviceability": settings.service_agent_llm,
            "carrier": settings.carrier_agent_llm,
        }
        model_name = agent_models.get(agent_type, settings.supervisor_llm)
    
    return LiteLLMAdapter(model_name=model_name)


@lru_cache
def get_cached_llm_provider(agent_type: str) -> LLMProvider:
    """
    Get a cached LLM provider instance for an agent type.
    
    This is useful for reusing provider instances across multiple calls.
    
    Args:
        agent_type: Agent type ("supervisor", "rate", "serviceability", "carrier")
        
    Returns:
        Cached LLMProvider instance.
    """
    return get_llm_provider(agent_type=agent_type)
