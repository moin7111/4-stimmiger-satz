# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Create non-root user
RUN useradd -m -u 10001 appuser

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application
COPY server /app/server

# Drop caps and run as non-root
USER appuser

EXPOSE 8501

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "streamlit", "run", "server/app_streamlit.py", "--server.port", "8501", "--server.headless", "true", "--server.address", "0.0.0.0"]

