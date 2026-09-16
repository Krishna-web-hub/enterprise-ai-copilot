# ============================================================
# Backend Dockerfile - Production-optimized multi-stage build
# ============================================================
# Stage 1: Install dependencies (cached unless requirements.txt changes)
# Stage 2: Production runtime (non-root user, minimal attack surface)
#
# Build: docker build -t copilot-backend .
# Run:   docker run -p 8000:8000 --env-file .env copilot-backend

# ─── Stage 1: Dependencies ─────────────────────────────────
FROM python:3.12-slim AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Configure apt to use HTTPS repositories for reliable network fetching
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

# System deps for Python packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (using CPU index for PyTorch to avoid 2GB CUDA bloat)
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# ─── Stage 2: Production Runtime ───────────────────────────
FROM dependencies AS production

# Create non-root user (never run containers as root in production)
RUN useradd --create-home --shell /bin/bash appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directories with correct ownership
RUN mkdir -p data/uploads data/models && \
    chown -R appuser:appuser /app/data

# Switch to non-root user
USER appuser

# Expose port (Cloud Run defaults to 8080)
ENV PORT=8080
EXPOSE 8080

# Health check supporting dynamic $PORT
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8080'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

# Production command with dynamic PORT expansion and exec signal forwarding
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers ${BACKEND_WORKERS:-1}"]
