#!/bin/bash
# Start Enterprise AI Copilot (with persistent data)
# Run: bash start.sh

set -e
cd "$(dirname "$0")"

echo "Starting PostgreSQL (persistent)..."
docker rm -f copilot-postgres 2>/dev/null || true
docker run -d --name copilot-postgres \
  -e POSTGRES_DB=ai_copilot \
  -e POSTGRES_USER=copilot_user \
  -e POSTGRES_PASSWORD=devpass123 \
  -p 5432:5432 \
  -v "$(pwd)/data/postgres:/var/lib/postgresql/data" \
  postgres:15-alpine

echo "Starting Redis (persistent)..."
docker rm -f copilot-redis 2>/dev/null || true
docker run -d --name copilot-redis \
  -p 6379:6379 \
  -v "$(pwd)/data/redis:/data" \
  redis:7-alpine redis-server --appendonly yes

echo "Waiting for databases..."
sleep 5

echo "Running migrations..."
cd backend
.venv/bin/python -m alembic upgrade head

echo "Starting backend..."
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

echo "Starting frontend..."
cd ../frontend
npm run dev &

echo ""
echo "✅ All services running:"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   Data persisted in: ./data/"
echo ""
wait
