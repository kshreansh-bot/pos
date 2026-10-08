"""Alembic migrations environment configuration."""
from logging.config import fileConfig
from multiprocessing import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic.config import Config
import os

# Add app to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models import Base


def get_url():
    """Get database URL for migrations."""
    return settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations(connection: Connection) -> None:
    """Run migrations using a synchronous database connection."""
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run async migrations for async SQLite."""
    configuration = {"sqlalchemy.url": get_url()}
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(run_migrations)


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    connectable = engine = None

    # For async SQLite, use offline mode or custom handling
    from sqlalchemy import create_engine
    sync_url = settings.database_url.replace("+aiosqlite", "")
    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()