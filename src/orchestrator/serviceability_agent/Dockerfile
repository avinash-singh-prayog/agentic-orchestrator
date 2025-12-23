FROM python:3.12-slim

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml .

# Create virtual environment and install dependencies
RUN uv venv && uv pip install -r pyproject.toml

# Copy application code
COPY . .

# Expose port
EXPOSE 9003

# Run the application
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9003"]
