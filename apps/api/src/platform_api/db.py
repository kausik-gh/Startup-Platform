import os
from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


_RESET_GUCS = text(
    "SELECT set_config('app.current_business_id', '', false), "
    "set_config('app.current_identity_id', '', false)"
)

# The GUC reset only matters when the API is on the RLS-enforcing connection —
# there it stops a pooled connection from carrying one request's tenant scope
# into the next. On the bypass connection (API_DATABASE_URL unset) it is pure
# overhead: an extra transaction per request, which at test-suite parallelism
# adds enough connection pressure against the 15-slot pooler to tip load-
# sensitive tests over. So gate it on enforcement being active.
_RLS_ENFORCING = os.getenv("API_DATABASE_URL") is not None


async def _reset_and_close(session: AsyncSession) -> None:
    """Clear the RLS session GUCs before the connection returns to the pool.

    `bind_session_context` sets them at SESSION scope so they survive a
    handler's commits; without this reset the next request to reuse the
    connection would inherit the previous tenant's scope until it re-binds
    (and a public/unbound path would inherit it outright). Best-effort — a
    failed reset just means that connection stays bound until its next bind,
    which every authenticated request performs.
    """
    if not _RLS_ENFORCING:
        return
    try:
        await session.rollback()
        await session.execute(_RESET_GUCS)
        await session.commit()
    except Exception:
        pass


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    # db_session_factory is stored in app.state during lifespan
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if session_factory is not None:
        async with session_factory() as session:
            try:
                yield session
            finally:
                await _reset_and_close(session)
        return

    # Fallback: lifespan never ran (e.g. TestClient(app) instantiated without
    # entering the lifespan context). Build a throwaway engine per call with
    # NullPool so no connection is pooled beyond this request — a cached pool
    # on app.state would outlive the caller's event loop and break across
    # independent TestClient(app) instances. Mirrors the URL handling and
    # session construction in platform_core.db.create_worker_session_factory.
    #
    # Uses API_DATABASE_URL (the RLS-enforcing role) when set, so the test
    # suite actually exercises the policies rather than the bypass path.
    db_url = os.getenv("API_DATABASE_URL") or os.getenv("DATABASE_URL")
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


async def get_service_db_session() -> AsyncGenerator[AsyncSession, None]:
    """A session on the `postgres` (rolbypassrls) connection.

    For the handful of endpoints that legitimately cross tenant boundaries and
    cannot be expressed as a row-level policy — Super Admin inspection
    (Doc 11 §17.7: "Admin can inspect and support") and the payment provider
    webhook (no business context; the signature is the auth). Every such
    endpoint enforces its own gate: `require_super_admin` for admin,
    `verify_webhook_signature` for the webhook. Uses DATABASE_URL, never
    API_DATABASE_URL.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    try:
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
