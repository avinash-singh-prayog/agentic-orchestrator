FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy workspace configuration and lockfile from root
COPY pyproject.toml uv.lock ./

# Copy the specific package configuration
COPY src/orchestrator/carrier_agent/pyproject.toml src/orchestrator/carrier_agent/
COPY src/orchestrator/carrier_agent/README.md src/orchestrator/carrier_agent/

# Sync dependencies for the specific package
# This leverages the lockfile from the root
RUN uv sync --frozen --package carrier-agent

# Copy the source code
COPY src/orchestrator/carrier_agent src/orchestrator/carrier_agent

# Set pythonpath to find the module
ENV PYTHONPATH=/app/src/orchestrator

# Expose port
EXPOSE 8000

# Run the application
# Note: We use the venv created by uv sync at the root /app/.venv
CMD ["/app/.venv/bin/uvicorn", "carrier_agent.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
