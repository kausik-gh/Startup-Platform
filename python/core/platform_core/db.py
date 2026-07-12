import os
from typing import Tuple, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)


def get_database_url() -> str | None:
    # Explicitly check for DATABASE_URL; no masked defaults.
    return os.getenv("DATABASE_URL")


def create_worker_session_factory(
    role: str = "service",
) -> Tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Creates an async engine and session factory.
    role: "service" (RLS bypassed, e.g. for worker processes) or "user" (RLS active)
    """
    db_url = get_database_url()
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # In asyncpg, we must use postgresql+asyncpg
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
    )

    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, factory


@asynccontextmanager
async def transactional_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Foundational transaction helper for operations that require atomic commits
    (e.g., domain mutation + outbox event insert).
    """
    async with session_factory() as session:
        async with session.begin():
            yield session
