FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY server.py .
COPY .env.example .env

# Install dependencies directly (not as a package)
RUN pip install --no-cache-dir fastmcp httpx python-dotenv

# Environment
ENV PYTHONUNBUFFERED=1

# FastMCP SSE server runs on port 8000 by default
EXPOSE 8000

# Run with SSE transport on 0.0.0.0 (accessible from other containers)
CMD ["python", "-c", "from server import mcp; mcp.run(transport='sse', host='0.0.0.0')"]
