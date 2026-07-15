#!/bin/bash
# Start all backend services for Enterprise AI Copilot

set -e

echo "🔧 Starting PostgreSQL..."
docker rm -f copilot-postgres 2>/dev/null || true
docker run -d --name copilot-postgres \
  -e POSTGRES_DB=ai_copilot \
  -e POSTGRES_USER=copilot_user \
  -e POSTGRES_PASSWORD=devpass123 \
  -p 5432:5432 \
  postgres:15-alpine

echo "🔧 Starting Redis..."
docker rm -f copilot-redis 2>/dev/null || true
docker run -d --name copilot-redis \
  -p 6379:6379 \
  redis:7-alpine

echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

echo "🗄️  Running database migrations..."
cd /home/master-krishna-kiran/enterprise-ai-copilot/backend
source .venv/bin/activate
alembic upgrade head

echo "🚀 Starting FastAPI backend on port 8000..."
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
