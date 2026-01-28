FROM python:3.12-slim

WORKDIR /app

# Install uv and dirctl
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ADD https://github.com/agntcy/dir/releases/download/v0.6.0/dirctl-linux-amd64 /usr/local/bin/dirctl
RUN chmod +x /usr/local/bin/dirctl

# Copy shared libraries first (from parent build context)
COPY libs /app/libs

# Copy project files
COPY personal_assistant_agent/pyproject.toml .
COPY personal_assistant_agent/agent_record.json .

# Copy application code
COPY personal_assistant_agent/config/ config/
COPY personal_assistant_agent/agent/ agent/
COPY personal_assistant_agent/tools/ tools/
COPY personal_assistant_agent/app/ app/

# Install dependencies
ENV UV_HTTP_TIMEOUT=300
RUN uv venv && uv pip install . && uv pip install pydantic

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 9006

# Run in dual mode (HTTP + SLIM)
CMD ["sh", "-c", "PYTHONPATH=/app /app/.venv/bin/python -m app.main dual"]
