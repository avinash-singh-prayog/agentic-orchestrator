# Weather MCP Server

A Model Context Protocol (MCP) server that provides weather data tools using the fastmcp library.

## Features

- **get_current_weather**: Get current weather conditions for any location
- **get_weather_forecast**: Get multi-day forecast (up to 5 days)
- **Vendor-agnostic**: Provider pattern allows switching weather APIs

## Installation

```bash
cd src/orchestrator/mcp_servers/weather
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# Edit .env with your OpenWeatherMap API key
```

Get a free API key from: https://openweathermap.org/api

## Running

### Standalone (stdio transport)
```bash
python server.py
```

### With Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "OPENWEATHERMAP_API_KEY": "your-api-key"
      }
    }
  }
}
```

### With FastMCP dev server
```bash
fastmcp dev server.py
```

## Example Usage

Once connected, you can ask:
- "What's the weather in Tokyo?"
- "Get me a 3-day forecast for New York"
- "Current conditions in London, UK"
