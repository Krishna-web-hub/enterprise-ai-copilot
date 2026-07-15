"""
Application Configuration

Uses Pydantic Settings to load environment variables with validation and defaults.
This is the single source of truth for all configuration values across the application.

Why Pydantic Settings?
- Type validation at startup (fail fast if config is wrong)
- Default values with override from .env
- IDE autocompletion for all settings
- Immutable after creation (prevents accidental mutation)
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic automatically reads from .env file and validates types.
    If a required field is missing, the app fails to start with a clear error.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ───────────────────────────────────────────
    APP_NAME: str = "Enterprise AI Analytics Copilot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ─── Backend Server ────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_WORKERS: int = 1

    # ─── Frontend ──────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    # ─── Database ──────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ai_copilot"
    POSTGRES_USER: str = "copilot_user"
    POSTGRES_PASSWORD: str = "change_me_in_production"

    # ─── Redis ─────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # ─── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── LLM Provider ────────────────────────────────────────────
    # Supports OpenAI, HuggingFace Inference API, or any OpenAI-compatible endpoint.
    # For HuggingFace: set LLM_BASE_URL and LLM_API_KEY, use model name like "Qwen/Qwen2.5-72B-Instruct"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""  # Leave empty for OpenAI, or set to "https://router.huggingface.co/v1" for HF
    LLM_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"
    LLM_EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_TEMPERATURE: float = 0.1  # Low temperature for deterministic SQL generation

    # Legacy OpenAI settings (kept for backward compatibility)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ─── SQL Engine ────────────────────────────────────────────
    SQL_MAX_ROWS: int = 1000  # Hard cap on rows returned from any query
    SQL_QUERY_TIMEOUT_SECONDS: int = 15  # Kill queries that run longer than this

    # ─── Vector Database ───────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "documents"

    # ─── File Storage ──────────────────────────────────────────
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 100
    MODELS_DIR: str = "./data/models"
    STORAGE_BACKEND: str = "local"  # "local" or "s3"

    # ─── AWS S3 (when STORAGE_BACKEND=s3) ──────────────────────
    S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str = ""  # For S3-compatible services (MinIO, etc.)

    # ─── ML Engine ─────────────────────────────────────────────
    ML_CV_FOLDS: int = 3  # Cross-validation folds for algorithm auto-selection
    ML_TEST_SIZE: float = 0.2  # Holdout fraction for final evaluation
    ML_SHAP_SAMPLE_SIZE: int = 100  # Max rows used to compute SHAP values (perf)

    # ─── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ─── Rate Limiting ─────────────────────────────────────────
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # Sliding window duration

    # ─── Computed Properties ───────────────────────────────────

    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection string for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync PostgreSQL connection string (for Alembic migrations)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Redis connection string."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        # If wildcard is present, return just ["*"] for allow-all
        if "*" in origins:
            return ["*"]
        return origins

    @property
    def upload_path(self) -> Path:
        """Resolved upload directory path."""
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def models_path(self) -> Path:
        """Resolved directory for persisted trained ML model artifacts."""
        path = Path(self.MODELS_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton settings instance - imported throughout the application
settings = Settings()
