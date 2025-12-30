# MCP Servers

This directory contains Model Context Protocol (MCP) servers built with [fastmcp](https://gofastmcp.com/).

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) is a standard for LLMs to access external tools and data. MCP servers expose:
- **Tools**: Functions the LLM can call (like API endpoints)
- **Resources**: Data the LLM can read (like files)
- **Prompts**: Reusable interaction patterns

## Available Servers

| Server | Description | Tools |
|--------|-------------|-------|
| [weather](./weather/) | Weather data provider | `get_current_weather`, `get_weather_forecast` |
| [websearch](./websearch/) | Web search & extraction | `search_web`, `extract_content` |

## Running MCP Servers

### With Docker Compose (Recommended)

```bash
# From project root
docker compose up -d weather-mcp websearch-mcp

# Check logs
docker compose logs -f weather-mcp
```

The servers will be available at:
- Weather MCP: `http://localhost:8003/sse`
- WebSearch MCP: `http://localhost:8004/sse`

### Development Mode (Local)

```bash
# Install fastmcp
pip install fastmcp

# Run with dev server (includes web UI)
cd weather
fastmcp dev server.py
```

### With Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/full/path/to/weather/server.py"],
      "env": {
        "OPENWEATHERMAP_API_KEY": "your-key"
      }
    },
    "websearch": {
      "command": "python",
      "args": ["/full/path/to/websearch/server.py"],
      "env": {
        "TAVILY_API_KEY": "your-key"
      }
    }
  }
}
```

## API Keys Required

| Server | API Key | Get From |
|--------|---------|----------|
| weather | `OPENWEATHERMAP_API_KEY` | [openweathermap.org/api](https://openweathermap.org/api) |
| websearch | `TAVILY_API_KEY` | [tavily.com](https://tavily.com) |

## Adding New MCP Servers

1. Create a new directory: `mkdir new_server`
2. Create `server.py` using fastmcp:
   ```python
   from fastmcp import FastMCP
   
   mcp = FastMCP("MyServer")
   
   @mcp.tool
   def my_tool(param: str) -> str:
       """Tool description."""
       return f"Result for {param}"
   
   if __name__ == "__main__":
       mcp.run()
   ```
3. Add `pyproject.toml` with dependencies
4. Add `README.md` with usage instructions
