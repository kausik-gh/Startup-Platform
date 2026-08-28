import os
from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    # db_session_factory is stored in app.state during lifespan
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if session_factory is not None:
        async with session_factory() as session:
            yield session
        return

    # Fallback: lifespan never ran (e.g. TestClient(app) instantiated without
    # entering the lifespan context). Build a throwaway engine per call with
    # NullPool so no connection is pooled beyond this request — a cached pool
    # on app.state would outlive the caller's event loop and break across
    # independent TestClient(app) instances. Mirrors the URL handling and
    # session construction in platform_core.db.create_worker_session_factory.
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("Database session factory is not initialized")

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    try:
        factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
