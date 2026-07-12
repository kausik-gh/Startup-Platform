from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    # db_session_factory is stored in app.state during lifespan
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if not session_factory:
        raise RuntimeError("Database session factory is not initialized")

    async with session_factory() as session:
        yield session
