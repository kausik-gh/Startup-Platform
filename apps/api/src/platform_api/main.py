import os
from typing import Any, AsyncIterator
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
from platform_core.db import create_worker_session_factory
from platform_core.exceptions import PlatformError
from platform_api.errors import platform_error_handler
from platform_api.rate_limit import RateLimitMiddleware
from platform_api.routers import me, v1_me, v1_businesses, v1_business, v1_team_modules, v1_admin, v1_platform_members, v1_platform_invitations, v1_platform_settings, v1_platform_configuration, v1_platform_entitlements, v1_platform_permissions, v1_platform_locations, v1_platform_employees, v1_platform_customers, v1_platform_offerings, v1_platform_inventory, v1_platform_orders, v1_platform_bookings, v1_platform_payments, webhooks_payments, v1_website, v1_public_websites, v1_public_search, v1_marketplace, v1_fulfilment, v1_public_checkout, v1_workforce, v1_public_bookings, v1_platform_leads, v1_platform_memberships, v1_platform_notifications

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

    # Clear the advertised factory before disposing its engine. Leaving a
    # disposed engine on app.state makes get_db_session hand out sessions bound
    # to a closed event loop and suppresses its NullPool fallback — which breaks
    # every later bare-TestClient(app) test in the same process once any
    # `with TestClient(app)` test has run lifespan.
    app.state.db_session_factory = None
    if db_engine:
        await db_engine.dispose()
    db_engine = None
    db_session_factory = None


app = FastAPI(
    title="Multi-Tenant Platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting (Doc 11 §21.1 gate 8). Added BEFORE CORS so CORS ends up the
# outer layer (Starlette wraps last-added first): a 429 short-circuited here
# still travels back out through CORS and gets its headers, so a browser sees
# the 429 rather than an opaque network error. Opt out per-process with
# RATE_LIMIT_ENABLED=0 — the test suite does, so parallel workers hammering
# shared buckets don't trip each other.
if os.getenv("RATE_LIMIT_ENABLED", "1") != "0":
    app.add_middleware(RateLimitMiddleware)

# Standard CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me.router)
app.include_router(v1_me.router)
app.include_router(v1_businesses.router)
app.include_router(v1_platform_members.router)
app.include_router(v1_platform_invitations.router)
app.include_router(v1_platform_settings.router)
app.include_router(v1_platform_configuration.router)
app.include_router(v1_platform_entitlements.router)
app.include_router(v1_platform_permissions.router)
app.include_router(v1_platform_locations.router)
app.include_router(v1_platform_employees.router)
app.include_router(v1_platform_customers.router)
app.include_router(v1_platform_offerings.router)
app.include_router(v1_platform_inventory.router)
app.include_router(v1_platform_orders.router)
app.include_router(v1_platform_bookings.router)
app.include_router(v1_workforce.router)
app.include_router(v1_platform_payments.router)
app.include_router(webhooks_payments.router)
app.include_router(v1_website.router)
app.include_router(v1_public_websites.router)
app.include_router(v1_public_search.router)
app.include_router(v1_marketplace.router)
app.include_router(v1_fulfilment.router)
app.include_router(v1_public_checkout.router)
app.include_router(v1_public_bookings.router)
app.include_router(v1_business.router)
app.include_router(v1_team_modules.router)
app.include_router(v1_admin.router)
app.include_router(v1_platform_leads.router)
app.include_router(v1_platform_memberships.router)
app.include_router(v1_platform_notifications.router)

app.add_exception_handler(PlatformError, platform_error_handler)


@app.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, Any]:
    """
    Liveness check to verify the process is alive.
    """
    return {"status": "ok", "message": "Liveness check passed"}


@app.get("/health/ready")
async def readiness_check(request: Request, response: Response) -> dict[str, Any]:
    """
    Readiness check to verify DB connection and required services.
    """
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if not session_factory:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "database": "not_configured",
            "message": "Database is not configured",
        }

    try:
        async with session_factory() as session:
            # Perform a quick select to verify connectivity
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "message": f"Database connectivity failed: {str(e)}"}


@app.get("/health/worker")
async def worker_health_check(request: Request, response: Response) -> dict[str, Any]:
    """Worker/outbox lag health gate (Doc 12 §22.2)."""
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if not session_factory:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "worker": "not_configured",
            "message": "Database is not configured",
        }

    lag_threshold_seconds = int(os.getenv("WORKER_LAG_THRESHOLD_SECONDS", "300"))
    try:
        async with session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT COALESCE(
                        EXTRACT(EPOCH FROM (now() - MIN(created_at))),
                        0
                    )::int AS lag_seconds,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending_count
                    FROM platform_outbox_events
                    WHERE status IN ('pending', 'processing')
                """)
            )
            row = result.one()
            lag_seconds = int(row.lag_seconds or 0)
            pending_count = int(row.pending_count or 0)
        if lag_seconds > lag_threshold_seconds and pending_count > 0:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "error",
                "worker": "lag_exceeded",
                "lag_seconds": lag_seconds,
                "pending_count": pending_count,
            }
        return {
            "status": "ok",
            "worker": "healthy",
            "lag_seconds": lag_seconds,
            "pending_count": pending_count,
        }
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "message": f"Worker health check failed: {str(e)}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("platform_api.main:app", host="0.0.0.0", port=8000, reload=True)
