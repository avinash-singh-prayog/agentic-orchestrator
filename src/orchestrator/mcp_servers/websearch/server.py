"""
Web Search MCP Server.

A true MCP server using fastmcp library that provides web search tools.
Uses vendor-agnostic provider pattern (Tavily default).
"""
import os
import logging
from typing import Optional
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websearch_mcp")

# Configuration
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "tavily")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_BASE_URL = "https://api.tavily.com"

# Create the FastMCP server
mcp = FastMCP(
    "WebSearch",
    instructions="""
    Web Search MCP Server provides tools for searching the web and extracting content.
    
    Available tools:
    - search_web: Search the web for information on any topic (returns AI-summarized results)
    - extract_content: Extract and summarize content from a specific URL
    
    The search tool returns both individual results and an AI-generated summary answer.
    """
)


# =============================================================================
# Search Provider Implementation
# =============================================================================

@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    score: Optional[float] = None


@dataclass  
class SearchResponse:
    """Search response with results and optional AI answer."""
    query: str
    results: list[SearchResult]
    answer: Optional[str] = None


async def search_with_tavily(query: str, max_results: int = 5) -> SearchResponse:
    """Search using Tavily API."""
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not configured. Set it in your environment.")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{TAVILY_BASE_URL}/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "include_images": False,
                "max_results": max_results,
            }
        )
        
        if response.status_code == 401:
            raise ValueError("Invalid Tavily API key")
        elif response.status_code == 429:
            raise ValueError("Tavily rate limit exceeded")
        elif response.status_code != 200:
            raise ValueError(f"Tavily API error: {response.status_code}")
        
        data = response.json()
        
        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", "")[:300],
                score=r.get("score")
            )
            for r in data.get("results", [])
        ]
        
        return SearchResponse(
            query=query,
            results=results,
            answer=data.get("answer")
        )


async def extract_url_content(url: str) -> dict:
    """Extract content from a URL using web scraping."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        
        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        # Get title
        title = soup.title.string.strip() if soup.title else None
        
        # Get main content
        main = soup.find("main") or soup.find("article") or soup.body
        text = main.get_text(separator="\n", strip=True) if main else ""
        
        # Clean up
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        content = "\n".join(lines)[:3000]
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "word_count": len(content.split())
        }


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool
async def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web for information on any topic.
    
    Args:
        query: The search query (e.g., "latest AI news", "Python best practices 2024")
        max_results: Maximum number of results to return (1-10, default 5)
    
    Returns:
        Search results with titles, URLs, snippets, and an AI-generated summary answer.
    """
    logger.info(f"Searching web for: {query}")
    
    # Clamp max_results
    max_results = max(1, min(max_results, 10))
    
    try:
        response = await search_with_tavily(query, max_results)
        
        lines = [f"🔍 **Search results for:** {query}\n"]
        
        # Add AI answer if available
        if response.answer:
            lines.append(f"**Summary:** {response.answer}\n")
        
        # Add individual results
        for i, result in enumerate(response.results, 1):
            lines.append(f"{i}. [{result.title}]({result.url})")
            if result.snippet:
                lines.append(f"   {result.snippet[:150]}...")
            lines.append("")
        
        if not response.results:
            lines.append("No results found.")
        
        return "\n".join(lines)
        
    except ValueError as e:
        return f"❌ Error: {str(e)}"
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"❌ Search failed: {str(e)}"


@mcp.tool
async def extract_content(url: str) -> str:
    """
    Extract and summarize content from a URL.
    
    Args:
        url: The URL to extract content from (e.g., "https://example.com/article")
    
    Returns:
        The extracted title and main content from the page.
    """
    logger.info(f"Extracting content from: {url}")
    
    try:
        result = await extract_url_content(url)
        
        lines = [f"📄 **Content from:** [{result['title'] or 'Untitled'}]({result['url']})\n"]
        lines.append(f"*({result['word_count']} words)*\n")
        lines.append("---")
        lines.append(result["content"])
        
        return "\n".join(lines)
        
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP error fetching URL: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Content extraction failed: {e}")
        return f"❌ Failed to extract content: {str(e)}"


# =============================================================================
# MCP Resources
# =============================================================================

@mcp.resource("search://config")
def get_search_config() -> str:
    """Get the current search server configuration."""
    return f"""Web Search MCP Server Configuration:
- Provider: {SEARCH_PROVIDER}
- Tavily API Key Configured: {'Yes' if TAVILY_API_KEY else 'No'}
"""


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
