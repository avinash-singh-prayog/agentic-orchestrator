FROM python:3.12-slim

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Download dirctl binary for directory service registration
ADD https://github.com/agntcy/dir/releases/download/v0.6.0/dirctl-linux-amd64 /usr/local/bin/dirctl
RUN chmod +x /usr/local/bin/dirctl

# Copy dependency files first for better cache utilization
COPY pyproject.toml .

# Copy application code (needed for package install)
COPY . .

# Create virtual environment and install project with dependencies
RUN uv venv && uv pip install .

# Expose port
EXPOSE 9004

# Run the application
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9004"]
