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

# System deps for Python packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (this layer is cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "torch==2.5.1+cpu" "torchvision==0.20.1+cpu" \
       --index-url https://download.pytorch.org/whl/cpu

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

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production command with multiple workers
# Workers = 2 * CPU_CORES + 1 (can be overridden via env)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
