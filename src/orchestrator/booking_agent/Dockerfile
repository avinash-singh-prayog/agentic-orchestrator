# Build context should be the repo root (.)
# Usage: docker build -f src/orchestrator/booking_agent/Dockerfile .

FROM python:3.12-slim

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy the agent directory as a Python package
COPY src/orchestrator/booking_agent /app/booking_agent

# Create virtual environment and install project and dependencies
RUN uv venv && uv pip install /app/booking_agent

# Expose port
EXPOSE 9005

# Default command (can be overridden in docker-compose)
CMD ["/app/.venv/bin/python", "-m", "booking_agent.app.main"]
