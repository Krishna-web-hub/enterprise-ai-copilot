#!/bin/bash
# ============================================================
# Docker Compose Production Deployment Script
# ============================================================
# Deploys the full stack on a single server using docker-compose.prod.yml
#
# Prerequisites:
# - Docker and Docker Compose installed
# - .env.production file configured
# - SSL certs in deploy/nginx/ssl/ (optional, HTTP-only without)
#
# Usage:
#   ./deploy/scripts/deploy-docker.sh [build|up|down|restart|logs|status]

set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
PROJECT="ai-copilot"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

check_prerequisites() {
    command -v docker >/dev/null 2>&1 || error "Docker is not installed"
    command -v docker compose >/dev/null 2>&1 || error "Docker Compose is not installed"

    if [ ! -f "$ENV_FILE" ]; then
        error "Missing $ENV_FILE. Copy .env.example to $ENV_FILE and configure it."
    fi
}

build() {
    log "Building production images..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" -p "$PROJECT" build
    log "Build complete."
}

up() {
    check_prerequisites
    log "Starting production services..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" -p "$PROJECT" up -d
    log "Waiting for services to be healthy..."
    sleep 10
    status
}

down() {
    log "Stopping services..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" -p "$PROJECT" down
    log "Services stopped."
}

restart() {
    log "Restarting services..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" -p "$PROJECT" restart
    log "Services restarted."
}

logs() {
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" -p "$PROJECT" logs -f --tail=100
}

status() {
    log "Service status:"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" -p "$PROJECT" ps

    echo ""
    log "Health checks:"
    echo -n "  Backend: "
    curl -sf http://localhost:80/health && echo " OK" || echo " UNHEALTHY"
}

# ─── Main ──────────────────────────────────────────────────────
case "${1:-up}" in
    build)   build ;;
    up)      up ;;
    down)    down ;;
    restart) restart ;;
    logs)    logs ;;
    status)  status ;;
    *)       echo "Usage: $0 [build|up|down|restart|logs|status]"; exit 1 ;;
esac
