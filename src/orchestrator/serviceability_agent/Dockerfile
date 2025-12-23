FROM python:3.12-slim

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files first for better cache utilization
COPY pyproject.toml .

# Copy application code (needed for package install)
COPY . .

# Create virtual environment and install project with dependencies
RUN uv venv && uv pip install .

# Expose port
EXPOSE 9003

# Run the application in dual mode (HTTP + SLIM)
# This enables both HTTP API server and SLIM listener for inter-agent communication
CMD ["sh", "-c", "PYTHONPATH=/app /app/.venv/bin/python -m app.main dual"]
