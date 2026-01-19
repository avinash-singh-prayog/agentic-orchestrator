"""
MCP Client for Personal Assistant Agent.

Provides weather and web search functionality.
Uses direct HTTP calls for reliability.
"""
import os
import logging
import asyncio
from typing import Any, Optional
from dataclasses import dataclass

import httpx

from config.settings import settings

logger = logging.getLogger("personal_assistant.mcp_client")

# OpenWeatherMap configuration
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org/data/2.5"


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    input_schema: dict


async def get_weather(location: str) -> str:
    """
    Get current weather for a location via OpenWeatherMap API directly.
    
    Args:
        location: City name (e.g., "London"), city with country (e.g., "Paris,FR")
    
    Returns:
        Weather information string
    """
    logger.info(f"Getting weather for: {location}")
    
    if not OPENWEATHERMAP_API_KEY:
        return "Error: OPENWEATHERMAP_API_KEY not configured"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{OPENWEATHERMAP_BASE_URL}/weather",
                params={
                    "q": location,
                    "appid": OPENWEATHERMAP_API_KEY,
                    "units": "metric"
                }
            )
            
            if response.status_code == 401:
                return "Error: Invalid OpenWeatherMap API key"
            elif response.status_code == 404:
                return f"Error: Location not found: {location}"
            elif response.status_code != 200:
                return f"Error: API error: {response.status_code}"
            
            data = response.json()
            
            loc_name = data.get("name", location)
            country = data.get("sys", {}).get("country", "")
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            description = data["weather"][0]["description"] if data.get("weather") else "Unknown"
            humidity = data["main"]["humidity"]
            wind_speed = data.get("wind", {}).get("speed", 0)
            pressure = data["main"]["pressure"]
            
            result = f"""📍 **{loc_name}**{f", {country}" if country else ""}

🌡️ **Temperature:** {temp:.1f}°C (feels like {feels_like:.1f}°C)
☁️ **Conditions:** {description.capitalize()}
💧 **Humidity:** {humidity}%
💨 **Wind:** {wind_speed:.1f} m/s
🔵 **Pressure:** {pressure} hPa"""
            
            logger.info(f"Weather retrieved successfully for {loc_name}")
            return result
            
    except httpx.TimeoutException:
        logger.error(f"Timeout getting weather for {location}")
        return f"Error: Timeout connecting to weather service"
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
        return f"Error: Failed to get weather: {str(e)}"


async def get_forecast(location: str, days: int = 5) -> str:
    """
    Get weather forecast for a location via OpenWeatherMap API directly.
    
    Args:
        location: City name
        days: Number of days (1-5)
    
    Returns:
        Forecast information string
    """
    logger.info(f"Getting {days}-day forecast for: {location}")
    
    if not OPENWEATHERMAP_API_KEY:
        return "Error: OPENWEATHERMAP_API_KEY not configured"
    
    days = max(1, min(days, 5))
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{OPENWEATHERMAP_BASE_URL}/forecast",
                params={
                    "q": location,
                    "appid": OPENWEATHERMAP_API_KEY,
                    "units": "metric",
                    "cnt": days * 8
                }
            )
            
            if response.status_code == 401:
                return "Error: Invalid OpenWeatherMap API key"
            elif response.status_code == 404:
                return f"Error: Location not found: {location}"
            elif response.status_code != 200:
                return f"Error: API error: {response.status_code}"
            
            data = response.json()
            city = data.get("city", {}).get("name", location)
            
            # Group by day
            from datetime import datetime
            daily: dict = {}
            for item in data.get("list", []):
                dt = datetime.fromtimestamp(item["dt"])
                date_key = dt.strftime("%Y-%m-%d")
                
                if date_key not in daily:
                    daily[date_key] = {
                        "date": dt.strftime("%a, %b %d"),
                        "temps": [],
                        "descriptions": []
                    }
                
                daily[date_key]["temps"].append(item["main"]["temp"])
                if item.get("weather"):
                    daily[date_key]["descriptions"].append(item["weather"][0]["description"])
            
            lines = [f"📍 **{city}** - {len(daily)}-Day Forecast\n"]
            for date_key in sorted(daily.keys())[:days]:
                day = daily[date_key]
                temps = day["temps"]
                desc = day["descriptions"][0] if day["descriptions"] else "Unknown"
                lines.append(f"**{day['date']}:** {min(temps):.0f}°C - {max(temps):.0f}°C, {desc.capitalize()}")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.error(f"Forecast fetch failed: {e}")
        return f"Error: Failed to get forecast: {str(e)}"


async def search_web(query: str, max_results: int = 5) -> str:
    """Search the web (placeholder - implement with actual search API)."""
    logger.info(f"Web search for: {query}")
    return f"Web search functionality is being set up. Please try again later or use a search engine directly for: {query}"


async def extract_content(url: str) -> str:
    """Extract content from URL (placeholder)."""
    logger.info(f"Extracting content from: {url}")
    return f"Content extraction is being set up. Please visit the URL directly: {url}"


# Legacy MCPClient class for compatibility
class MCPClient:
    """Legacy client - kept for compatibility."""
    def __init__(self, server_url: str, server_name: str):
        self.server_url = server_url
        self.server_name = server_name
    
    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        if tool_name == "get_current_weather":
            return await get_weather(arguments.get("location", ""))
        elif tool_name == "get_weather_forecast":
            return await get_forecast(arguments.get("location", ""), arguments.get("days", 5))
        elif tool_name == "search_web":
            return await search_web(arguments.get("query", ""), arguments.get("max_results", 5))
        elif tool_name == "extract_content":
            return await extract_content(arguments.get("url", ""))
        return f"Unknown tool: {tool_name}"
    
    async def close(self):
        pass


# Create clients for compatibility
weather_client = MCPClient(settings.weather_mcp_url, "weather")
websearch_client = MCPClient(settings.websearch_mcp_url, "websearch")
