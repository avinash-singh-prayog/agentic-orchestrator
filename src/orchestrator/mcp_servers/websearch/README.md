# Web Search MCP Server

A Model Context Protocol (MCP) server that provides web search and content extraction tools using the fastmcp library.

## Features

- **search_web**: Search the web with AI-summarized results (via Tavily)
- **extract_content**: Extract and parse content from any URL
- **Vendor-agnostic**: Provider pattern allows switching search APIs

## Installation

```bash
cd src/orchestrator/mcp_servers/websearch
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# Edit .env with your Tavily API key
```

Get a free API key from: https://tavily.com (1000 free searches/month)

## Running

### Standalone (stdio transport)
```bash
python server.py
```

### With Claude Desktop

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "websearch": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "TAVILY_API_KEY": "your-api-key"
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
- "Search for latest AI news"
- "Find Python best practices 2024"
- "Extract content from https://example.com/article"
