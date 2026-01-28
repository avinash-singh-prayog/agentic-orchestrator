FROM python:3.12-slim

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Download dirctl binary for directory service registration
ADD https://github.com/agntcy/dir/releases/download/v0.6.0/dirctl-linux-amd64 /usr/local/bin/dirctl
RUN chmod +x /usr/local/bin/dirctl

# Copy shared libraries first (from parent build context)
COPY libs /app/libs

# Copy dependency files for cache utilization
COPY serviceability_agent/pyproject.toml .

# Copy application code
COPY serviceability_agent/ .

# Create virtual environment and install project with dependencies
ENV UV_HTTP_TIMEOUT=300
RUN uv venv && uv pip install . && uv pip install pydantic

# Expose port
EXPOSE 9003

# Run the application in dual mode (HTTP + SLIM)
CMD ["sh", "-c", "PYTHONPATH=/app /app/.venv/bin/python -m app.main dual"]
