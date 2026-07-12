import os
from typing import Any, AsyncIterator
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
from platform_core.db import create_worker_session_factory
from platform_api.routers import me

# Database lifecycle state
db_engine = None
db_session_factory = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[Any]:
    global db_engine, db_session_factory

    if os.getenv("DATABASE_URL"):
        try:
            db_engine, db_session_factory = create_worker_session_factory()
        except Exception as e:
            print(f"Warning: Failed to initialize db session factory: {e}")
            db_engine = None
            db_session_factory = None

    app.state.db_session_factory = db_session_factory

    yield

    if db_engine:
        await db_engine.dispose()


app = FastAPI(
    title="Multi-Tenant Platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Standard CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me.router)


@app.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, Any]:
    """
    Liveness check to verify the process is alive.
    """
    return {"status": "ok", "message": "Liveness check passed"}


@app.get("/health/ready")
async def readiness_check(response: Response) -> dict[str, Any]:
    """
    Readiness check to verify DB connection and required services.
    """
    if not db_session_factory:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "database": "not_configured",
            "message": "Database is not configured",
        }

    try:
        async with db_session_factory() as session:
            # Perform a quick select to verify connectivity
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "message": f"Database connectivity failed: {str(e)}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("platform_api.main:app", host="0.0.0.0", port=8000, reload=True)
