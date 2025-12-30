"""
LangChain Tool Wrappers for MCP servers.

These tools wrap MCP server calls for use with the LangGraph agent.
"""
import logging
from langchain_core.tools import tool

from tools.mcp_client import get_weather, get_forecast, search_web, extract_content

logger = logging.getLogger("personal_assistant.tools")


@tool
async def get_current_weather(location: str) -> str:
    """
    Get the current weather conditions for a location.
    
    Use this tool when the user asks about current weather, temperature,
    or conditions in a specific location.
    
    Args:
        location: City name (e.g., "London"), city with country code (e.g., "Paris,FR"),
                  or zip code with country (e.g., "10001,US")
    
    Returns:
        Current weather including temperature, conditions, humidity, and wind.
    """
    logger.info(f"Getting weather for: {location}")
    return await get_weather(location)


@tool
async def get_weather_forecast(location: str, days: int = 5) -> str:
    """
    Get a multi-day weather forecast for a location.
    
    Use this tool when the user asks about future weather, forecasts,
    or what the weather will be like in coming days.
    
    Args:
        location: City name, city with country code, or zip code
        days: Number of days to forecast (1-5, default 5)
    
    Returns:
        Weather forecast showing temperature range and conditions for each day.
    """
    logger.info(f"Getting {days}-day forecast for: {location}")
    return await get_forecast(location, days)


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for information on any topic.
    
    Use this tool when the user asks questions that require current information
    from the internet, news, research, or topics you don't have knowledge about.
    
    Args:
        query: The search query (e.g., "latest AI news", "Python best practices 2024")
        max_results: Maximum number of results to return (1-10, default 5)
    
    Returns:
        Search results with titles, URLs, snippets, and an AI-generated summary.
    """
    logger.info(f"Searching web for: {query}")
    return await search_web(query, max_results)


@tool
async def read_webpage(url: str) -> str:
    """
    Extract and read content from a webpage URL.
    
    Use this tool when the user provides a URL and wants to know what's on that page,
    or when you need to read the full content of a search result.
    
    Args:
        url: The URL to extract content from (e.g., "https://example.com/article")
    
    Returns:
        The extracted title and main content from the webpage.
    """
    logger.info(f"Extracting content from: {url}")
    return await extract_content(url)


# Export all tools
PERSONAL_ASSISTANT_TOOLS = [
    get_current_weather,
    get_weather_forecast,
    web_search,
    read_webpage,
]
