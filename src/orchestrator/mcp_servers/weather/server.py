"""
Weather MCP Server.

A true MCP server using fastmcp library that provides weather data tools.
Uses vendor-agnostic provider pattern (OpenWeatherMap default).
"""
import os
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather_mcp")

# Configuration
WEATHER_PROVIDER = os.getenv("WEATHER_PROVIDER", "openweathermap")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org/data/2.5"

# Create the FastMCP server
mcp = FastMCP(
    "Weather",
    instructions="""
    Weather MCP Server provides current weather conditions and forecasts.
    
    Available tools:
    - get_current_weather: Get current weather for any location
    - get_weather_forecast: Get multi-day forecast for a location
    
    All temperatures are in Celsius. Locations can be city names, 
    "city,country" format, or zip codes.
    """
)


# =============================================================================
# Weather Provider Implementation
# =============================================================================

@dataclass
class WeatherData:
    """Weather data structure."""
    location: str
    country: Optional[str]
    temperature: float
    feels_like: float
    description: str
    humidity: int
    wind_speed: float
    pressure: int
    timestamp: datetime


async def fetch_weather_from_openweathermap(location: str) -> WeatherData:
    """Fetch weather from OpenWeatherMap API."""
    if not OPENWEATHERMAP_API_KEY:
        raise ValueError("OPENWEATHERMAP_API_KEY not configured. Set it in your environment.")
    
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
            raise ValueError("Invalid OpenWeatherMap API key")
        elif response.status_code == 404:
            raise ValueError(f"Location not found: {location}")
        elif response.status_code != 200:
            raise ValueError(f"API error: {response.status_code}")
        
        data = response.json()
        
        return WeatherData(
            location=data.get("name", location),
            country=data.get("sys", {}).get("country"),
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            description=data["weather"][0]["description"] if data.get("weather") else "Unknown",
            humidity=data["main"]["humidity"],
            wind_speed=data.get("wind", {}).get("speed", 0),
            pressure=data["main"]["pressure"],
            timestamp=datetime.utcnow()
        )


async def fetch_forecast_from_openweathermap(location: str, days: int = 5) -> list[dict]:
    """Fetch forecast from OpenWeatherMap API."""
    if not OPENWEATHERMAP_API_KEY:
        raise ValueError("OPENWEATHERMAP_API_KEY not configured. Set it in your environment.")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{OPENWEATHERMAP_BASE_URL}/forecast",
            params={
                "q": location,
                "appid": OPENWEATHERMAP_API_KEY,
                "units": "metric",
                "cnt": days * 8  # 3-hour intervals
            }
        )
        
        if response.status_code == 401:
            raise ValueError("Invalid OpenWeatherMap API key")
        elif response.status_code == 404:
            raise ValueError(f"Location not found: {location}")
        elif response.status_code != 200:
            raise ValueError(f"API error: {response.status_code}")
        
        data = response.json()
        city = data.get("city", {})
        
        # Group by day
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
        
        # Convert to list
        forecasts = []
        for date_key in sorted(daily.keys())[:days]:
            day = daily[date_key]
            temps = day["temps"]
            forecasts.append({
                "date": day["date"],
                "temp_min": round(min(temps), 1),
                "temp_max": round(max(temps), 1),
                "description": day["descriptions"][0] if day["descriptions"] else "Unknown"
            })
        
        return forecasts


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool
async def get_current_weather(location: str) -> str:
    """
    Get the current weather conditions for a location.
    
    Args:
        location: City name (e.g., "London"), city with country (e.g., "Paris,FR"), 
                  or zip code (e.g., "10001,US")
    
    Returns:
        Current weather information including temperature, conditions, humidity, and wind.
    """
    logger.info(f"Getting current weather for: {location}")
    
    try:
        weather = await fetch_weather_from_openweathermap(location)
        
        result = f"""📍 **{weather.location}**{f", {weather.country}" if weather.country else ""}

🌡️ **Temperature:** {weather.temperature:.1f}°C (feels like {weather.feels_like:.1f}°C)
☁️ **Conditions:** {weather.description.capitalize()}
💧 **Humidity:** {weather.humidity}%
💨 **Wind:** {weather.wind_speed:.1f} m/s
🔵 **Pressure:** {weather.pressure} hPa"""
        
        return result
        
    except ValueError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
        return f"❌ Failed to get weather: {str(e)}"


@mcp.tool
async def get_weather_forecast(location: str, days: int = 5) -> str:
    """
    Get a multi-day weather forecast for a location.
    
    Args:
        location: City name (e.g., "London"), city with country (e.g., "Paris,FR"),
                  or zip code (e.g., "10001,US")
        days: Number of days to forecast (1-5, default 5)
    
    Returns:
        Weather forecast showing temperature range and conditions for each day.
    """
    logger.info(f"Getting {days}-day forecast for: {location}")
    
    # Clamp days to valid range
    days = max(1, min(days, 5))
    
    try:
        forecasts = await fetch_forecast_from_openweathermap(location, days)
        
        if not forecasts:
            return f"❌ No forecast data available for {location}"
        
        lines = [f"📍 **{location}** - {len(forecasts)}-Day Forecast\n"]
        
        for day in forecasts:
            lines.append(f"**{day['date']}:** {day['temp_min']}°C - {day['temp_max']}°C, {day['description'].capitalize()}")
        
        return "\n".join(lines)
        
    except ValueError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        logger.error(f"Forecast fetch failed: {e}")
        return f"❌ Failed to get forecast: {str(e)}"


# =============================================================================
# MCP Resources (optional - for context loading)
# =============================================================================

@mcp.resource("weather://config")
def get_weather_config() -> str:
    """Get the current weather server configuration."""
    return f"""Weather MCP Server Configuration:
- Provider: {WEATHER_PROVIDER}
- API Key Configured: {'Yes' if OPENWEATHERMAP_API_KEY else 'No'}
- Base URL: {OPENWEATHERMAP_BASE_URL}
"""


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
