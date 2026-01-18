FROM python:3.13-slim

WORKDIR /app

# Install uv (fast python package manager)
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY app ./app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Bind to all interfaces for container deployment
ENV GATEWAY_HOST=0.0.0.0
ENV GATEWAY_PORT=7788

EXPOSE 7788

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${GATEWAY_PORT}"]
