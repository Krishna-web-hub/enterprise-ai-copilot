# Enterprise AI Analytics Copilot

[![Google Cloud Run](https://img.shields.io/badge/Google_Cloud_Run-Live_Deployment-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)](https://enterprise-ai-copilot-335067811983.asia-south1.run.app)
[![React](https://img.shields.io/badge/React_18-Web_UI-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://enterprise-ai-copilot-335067811983.asia-south1.run.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend_API-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://enterprise-ai-copilot-335067811983.asia-south1.run.app/docs)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

An enterprise-grade, full-stack AI analytics copilot that enables organizations to upload structured and unstructured datasets, query insights in natural language, and generate interactive dashboards, predictive machine learning models, deep learning computer vision analytics, and automated executive reports.

---

## 🚀 Live Production Links

| Service / Interface | Direct Link | Description |
| :--- | :--- | :--- |
| 🌐 **Interactive Web UI** | [enterprise-ai-copilot-335067811983.asia-south1.run.app](https://enterprise-ai-copilot-335067811983.asia-south1.run.app) | Single-page React application with dark/light mode, analytics dashboards, and copilot chat. |
| 📖 **Swagger API Docs** | [/docs](https://enterprise-ai-copilot-335067811983.asia-south1.run.app/docs) | Interactive OpenAPI / Swagger UI to test all REST endpoints. |
| 📋 **ReDoc Documentation** | [/redoc](https://enterprise-ai-copilot-335067811983.asia-south1.run.app/redoc) | Clean, structured API documentation specification. |
| 🩺 **Production Health Check** | [/health](https://enterprise-ai-copilot-335067811983.asia-south1.run.app/health) | Orchestrator liveness & readiness check for Google Cloud Run. |

---

## Architecture

```
Frontend (React + TypeScript + Tailwind)
    │
    ▼
FastAPI Gateway (Auth, Routing, Middleware)
    │
    ├── Auth Service
    ├── Data Management Service
    ├── SQL Engine (NL → SQL)
    ├── ML Engine (Training, Prediction)
    ├── Deep Learning Engine (Vision, OCR)
    ├── RAG Pipeline (Embeddings, Retrieval)
    ├── Agentic AI (LangGraph Orchestration)
    └── Report Generation
    │
    ▼
PostgreSQL │ Redis │ Qdrant │ Object Storage
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Tailwind CSS, Plotly |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Cache | Redis |
| Vector DB | Qdrant |
| ML | Scikit-learn, XGBoost, LightGBM |
| Deep Learning | PyTorch |
| GenAI | OpenAI API (swappable) |
| RAG | LangChain |
| Agents | LangGraph |
| Deployment | Docker, GitHub Actions |

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Quick Start (Docker)

```bash
# Clone the repository
git clone <repo-url>
cd enterprise-ai-copilot

# Copy environment variables
cp .env.example .env
# Edit .env with your values

# Start all services
docker compose up -d

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
enterprise-ai-copilot/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # API route handlers
│   │   ├── core/           # Config, security, database
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic layer
│   │   ├── agents/         # LangGraph agent definitions
│   │   ├── ml/             # ML training and prediction
│   │   ├── rag/            # RAG pipeline components
│   │   └── utils/          # Shared utilities
│   ├── data/               # Uploads, models, temp files
│   ├── migrations/         # Alembic database migrations
│   ├── tests/              # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route pages
│   │   ├── services/       # API client layer
│   │   ├── stores/         # State management
│   │   ├── hooks/          # Custom React hooks
│   │   └── types/          # TypeScript type definitions
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## Development Phases

- [x] Phase 0: Architecture & Planning
- [ ] Phase 1: Project Setup
- [ ] Phase 2: Authentication (JWT, Roles)
- [ ] Phase 3: Data Ingestion
- [ ] Phase 4: SQL Engine (NL → SQL)
- [ ] Phase 5: Machine Learning Engine
- [ ] Phase 6: Deep Learning Engine
- [ ] Phase 7: RAG Pipeline
- [ ] Phase 8: Agentic AI (LangGraph)
- [ ] Phase 9: Power BI Integration
- [ ] Phase 10: Generative AI Reports
- [x] Phase 11: Deployment & CI/CD (Google Cloud Run + Cloud Build)
- [ ] Phase 12: Optimization & Scaling

## License

MIT
