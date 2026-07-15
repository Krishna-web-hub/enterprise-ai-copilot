# Deployment Guide

## Quick Start (Development)

```bash
# 1. Clone the repository
git clone <repo-url> && cd enterprise-ai-copilot

# 2. Copy environment file and configure
cp .env.example .env
# Edit .env: set OPENAI_API_KEY, change JWT_SECRET_KEY

# 3. Start all services with Docker Compose
docker compose up -d

# 4. Access the application
# Frontend: http://localhost:5173
# Backend API docs: http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Frontend  │────▶│   Backend    │────▶│  PostgreSQL   │
│  (React)    │     │  (FastAPI)   │     │  (App data)   │
│  port 5173  │     │  port 8000   │     │  port 5432    │
└─────────────┘     └──────┬───────┘     └───────────────┘
                           │
                    ┌──────┼──────────┐
                    │      │          │
               ┌────▼──┐ ┌▼────┐ ┌───▼───┐
               │ Redis │ │Qdrant│ │OpenAI │
               │(cache)│ │(RAG) │ │ (LLM) │
               │ 6379  │ │ 6333 │ │  API  │
               └───────┘ └──────┘ └───────┘
```

## Services

| Service | Purpose | Port | Required |
|---------|---------|------|----------|
| Backend (FastAPI) | API server | 8000 | Yes |
| Frontend (React) | Web UI | 5173 (dev) / 80 (prod) | Yes |
| PostgreSQL | Application database | 5432 | Yes |
| Redis | Caching (future use) | 6379 | Optional |
| Qdrant | Vector DB for RAG | 6333 | For document Q&A |
| OpenAI API | LLM + Embeddings | External | For AI features |

## Environment Variables

See `.env.example` for all configuration options with descriptions.

**Minimum required for basic operation:**
- `POSTGRES_*` — Database connection
- `JWT_SECRET_KEY` — Authentication (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)

**Required for AI features:**
- `OPENAI_API_KEY` — Powers NL2SQL, RAG answers, report generation, agent planning

## Production Deployment

### Docker (Recommended)

```bash
# Build production images
docker build -t copilot-backend ./backend
docker build -t copilot-frontend ./frontend

# Run with production settings
docker run -d --name backend \
  --env-file .env.production \
  -p 8000:8000 \
  copilot-backend

docker run -d --name frontend \
  -p 80:80 \
  copilot-frontend
```

### Cloud Deployment Options

**Option 1: Kubernetes (production-grade, auto-scaling)**
```bash
# All manifests in k8s/ directory
./deploy/scripts/deploy-k8s.sh apply

# Features: 2-10 backend pods (HPA), rolling updates, TLS ingress,
# Prometheus metrics scraping, liveness/readiness/startup probes
```

**Option 2: AWS ECS Fargate (serverless containers)**
```bash
# Templates in deploy/aws/
# 1. Push images to ECR
# 2. Create ECS cluster, ALB, RDS, ElastiCache, S3 bucket
# 3. Register task definition: deploy/aws/ecs-task-definition.json
# 4. Create service: deploy/aws/ecs-service.json
# 5. Configure auto-scaling: deploy/aws/appautoscaling.json
```

**Option 3: Docker Compose (single server, simplest)**
```bash
# Production compose with nginx reverse proxy
cp deploy/.env.production.template .env.production
# Edit .env.production with your values
./deploy/scripts/deploy-docker.sh up
```

**Option 4: GCP Cloud Run / Azure Container Apps**
- Same Docker images work — just configure via cloud console
- Use managed PostgreSQL (Cloud SQL / Azure DB)
- Use managed Redis (Memorystore / Azure Cache)

### Production Checklist

- [ ] Set `DEBUG=false` and `APP_ENV=production`
- [ ] Generate strong `JWT_SECRET_KEY` (64+ hex chars)
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure CORS_ORIGINS to your actual domain
- [ ] Set `BACKEND_WORKERS` to `2 * CPU_CORES + 1`
- [ ] Enable HTTPS (via reverse proxy: nginx, Cloudflare, ALB)
- [ ] Set up database backups
- [ ] Configure log aggregation (CloudWatch, Datadog, etc.)
- [ ] Set up monitoring/alerting on `/health` endpoint
- [ ] Review and restrict `MAX_UPLOAD_SIZE_MB`

## Database Migrations

```bash
# Run migrations (from backend directory)
cd backend
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"
```

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`) runs on every push/PR:
1. **Backend**: Lint (ruff) → Test (pytest)
2. **Frontend**: TypeScript check → Lint → Build
3. **Docker**: Build images (push only)

## Monitoring

- **Health check**: `GET /health` — returns `{"status": "healthy"}` when the service is up
- **API docs**: `GET /docs` — Swagger UI showing all 33 endpoints
- **Request logging**: Every request logged with method, path, status code, duration

## Project Structure

```
enterprise-ai-copilot/
├── .github/workflows/ci.yml    # CI/CD pipeline
├── .env.example                # Environment template
├── docker-compose.yml          # Development orchestration
├── Makefile                    # Dev commands
├── backend/
│   ├── Dockerfile              # Production backend image
│   ├── requirements.txt        # Python dependencies (pinned)
│   ├── alembic.ini            # Migration configuration
│   ├── pytest.ini             # Test configuration
│   ├── migrations/            # Database migrations
│   ├── app/
│   │   ├── main.py           # FastAPI app factory + health check
│   │   ├── core/             # Config, DB, security, dependencies
│   │   ├── api/v1/endpoints/ # Route handlers
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic layer
│   │   ├── agents/           # Agentic AI (planner + specialized agents)
│   │   ├── ml/               # ML preprocessing + algorithm registry
│   │   ├── dl/               # Deep learning models (vision, OCR)
│   │   ├── rag/              # RAG (chunker, embeddings, vector store)
│   │   └── utils/            # Shared utilities
│   └── tests/                # 115 automated tests
└── frontend/
    ├── Dockerfile             # Production frontend image
    ├── package.json
    ├── src/
    │   ├── App.tsx           # Routing
    │   ├── pages/            # Page components
    │   ├── components/       # Shared components
    │   ├── services/         # API client layer
    │   ├── context/          # React context (auth)
    │   └── types/            # TypeScript type definitions
    └── nginx.conf            # Production SPA serving config
```
