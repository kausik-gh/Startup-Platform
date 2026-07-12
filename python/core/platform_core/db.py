import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


def get_database_url() -> str:
    # Use standard DATABASE_URL, fallback to a local postgres in dev/test
    return os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    )


def create_worker_session_factory(role: str = "service") -> async_sessionmaker[AsyncSession]:
    """
    Creates an async session factory.
    role: "service" (RLS bypassed, e.g. for worker processes) or "user" (RLS active)
    """
    db_url = get_database_url()

    # In asyncpg, we must use postgresql+asyncpg
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
    )

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
