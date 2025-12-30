"""
MCP Client for Personal Assistant Agent.

Connects to MCP servers (Weather, WebSearch) via SSE transport
and wraps their tools for use with LangChain.
"""
import logging
import asyncio
from typing import Any, Optional
from dataclasses import dataclass

import httpx

from config.settings import settings

logger = logging.getLogger("personal_assistant.mcp_client")


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    input_schema: dict


class MCPClient:
    """
    Client for connecting to MCP servers via SSE transport.
    
    This is a simplified client that calls MCP server tools via HTTP.
    For full SSE streaming, you would use the mcp library directly.
    """
    
    def __init__(self, server_url: str, server_name: str):
        self.server_url = server_url.rstrip("/")
        self.server_name = server_name
        self._client: Optional[httpx.AsyncClient] = None
        self._tools: list[MCPTool] = []
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def list_tools(self) -> list[MCPTool]:
        """List available tools from the MCP server."""
        # FastMCP exposes tools at /tools endpoint
        client = await self._get_client()
        
        try:
            # Try to get tool list from MCP server
            # Note: FastMCP SSE servers expose a JSON-RPC interface
            response = await client.post(
                f"{self.server_url.replace('/sse', '')}/",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                tools = data.get("result", {}).get("tools", [])
                self._tools = [
                    MCPTool(
                        name=t["name"],
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {})
                    )
                    for t in tools
                ]
                return self._tools
                
        except Exception as e:
            logger.warning(f"Could not list tools from {self.server_name}: {e}")
        
        return []
    
    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result as string
        """
        client = await self._get_client()
        
        try:
            response = await client.post(
                f"{self.server_url.replace('/sse', '')}/",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("result", {})
                
                # Extract text content
                content = result.get("content", [])
                if content and isinstance(content, list):
                    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    return "\n".join(texts) if texts else str(result)
                
                return str(result)
            else:
                return f"Error calling {tool_name}: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return f"Error: {str(e)}"
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Create MCP clients for our servers
weather_client = MCPClient(settings.weather_mcp_url, "weather")
websearch_client = MCPClient(settings.websearch_mcp_url, "websearch")


async def get_weather(location: str) -> str:
    """Get current weather for a location via Weather MCP."""
    return await weather_client.call_tool("get_current_weather", {"location": location})


async def get_forecast(location: str, days: int = 5) -> str:
    """Get weather forecast via Weather MCP."""
    return await weather_client.call_tool("get_weather_forecast", {"location": location, "days": days})


async def search_web(query: str, max_results: int = 5) -> str:
    """Search the web via WebSearch MCP."""
    return await websearch_client.call_tool("search_web", {"query": query, "max_results": max_results})


async def extract_content(url: str) -> str:
    """Extract content from URL via WebSearch MCP."""
    return await websearch_client.call_tool("extract_content", {"url": url})
