FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY server.py .
COPY .env.example .env

# Install dependencies directly (includes BeautifulSoup for content extraction)
RUN pip install --no-cache-dir fastmcp httpx python-dotenv beautifulsoup4 lxml

# Environment
ENV PYTHONUNBUFFERED=1

# FastMCP SSE server runs on port 8000 by default
EXPOSE 8000

# Run with SSE transport (HTTP-based)
CMD ["python", "-c", "from server import mcp; mcp.run(transport='sse')"]
