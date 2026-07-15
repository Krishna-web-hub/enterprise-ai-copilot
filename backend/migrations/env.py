"""
Alembic Migration Environment

This file configures how Alembic connects to the database and generates migrations.

Key concepts:
- target_metadata: Tells Alembic about your current model definitions
- run_migrations_online: Runs migrations against a live database
- run_migrations_offline: Generates SQL scripts without a database connection

Why async migrations?
- Our app uses async SQLAlchemy (asyncpg driver)
- Alembic needs to run migrations through the same async engine
- We use run_async() to bridge Alembic's sync API with our async engine
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Import all models so they're registered with Base.metadata
import app.models  # noqa: F401

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what Alembic compares against the database to detect changes
target_metadata = Base.metadata


def get_url() -> str:
    """Get the database URL from our app settings (not alembic.ini)."""
    return settings.database_url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    Generates SQL statements without connecting to the database.
    Useful for generating migration scripts to review before applying.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations using the provided database connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    
    Creates an async engine, connects, and runs migrations within
    the connection context.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the database)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
