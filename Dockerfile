# ============================================================
# Root Dockerfile for Cloud Build & Google Cloud Run
# ============================================================
# Compatible with Cloud Build context at repository root (.)
# Runs FastAPI backend with dynamic $PORT support, CPU-optimized
# PyTorch, non-root user, and zero reliance on local persistent disks.
# ============================================================

# ─── Stage 0: Build Frontend React UI ───────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=/api/v1
RUN npm run build

# ─── Stage 1: Build Dependencies ───────────────────────────
FROM python:3.12-slim AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Configure apt to use HTTPS repositories for reliable, secure network fetching
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

# Install system dependencies required for compilation, PostgreSQL, and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache dependencies installation layer
COPY backend/requirements.txt ./requirements.txt

# Install dependencies using CPU index for PyTorch to prevent downloading 2GB+ CUDA bloat
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# ─── Stage 2: Production Runtime ───────────────────────────
FROM dependencies AS production

# Security: Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy application code from backend directory
COPY backend/ .

# Copy compiled React frontend Web UI
COPY --from=frontend-builder /app/frontend/dist /app/static

# Ensure data directories exist and have proper non-root permissions
RUN mkdir -p /app/data/uploads /app/data/models && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Cloud Run injects the PORT environment variable (default: 8080)
ENV PORT=8080 \
    APP_ENV=production \
    DEBUG=false

EXPOSE 8080

# Health check using dynamic $PORT
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8080'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

# Start uvicorn with shell expansion for Cloud Run $PORT and exec for graceful SIGTERM signal handling
# Default to 1 worker for Cloud Run container memory efficiency
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers ${BACKEND_WORKERS:-1}"]
