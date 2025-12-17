FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy workspace configuration and lockfile from root
COPY pyproject.toml uv.lock ./

# Copy the specific package configuration
COPY src/orchestrator/booking_agent/pyproject.toml src/orchestrator/booking_agent/
COPY src/orchestrator/booking_agent/README.md src/orchestrator/booking_agent/

# Sync dependencies for the specific package
# This leverages the lockfile from the root
RUN uv sync --frozen --package booking-agent

# Copy the source code
COPY src/orchestrator/booking_agent src/orchestrator/booking_agent

# Set pythonpath to find the module
ENV PYTHONPATH=/app/src/orchestrator

# Expose port
EXPOSE 8000

# Run the application in dual mode (HTTP + SLIM)
# Note: We use the venv created by uv sync at the root /app/.venv
CMD ["/app/.venv/bin/python", "-m", "booking_agent.app.main", "dual"]
