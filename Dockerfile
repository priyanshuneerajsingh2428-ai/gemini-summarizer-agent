# =============================================================================
#  Multi-stage Dockerfile for ADK Summarizer Agent
#  Optimized for Google Cloud Run (linux/amd64)
# =============================================================================

# ---- Stage 1: dependency builder ----
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Create a venv for clean isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: lean runtime image ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the pre-built venv
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY main.py .
COPY agent/ agent/

# Cloud Run sets PORT automatically (default 8080)
ENV PORT=8080
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run as non-root for security
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8080

# 2 workers is a good starting point for Cloud Run min-instances=0
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 2 --log-level info"]
