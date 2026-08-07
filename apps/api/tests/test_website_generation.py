"""Stage 2 — Website generation: AI failure → fallback, never blocks creation."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import jwt
import pytest
from fastapi.testclient import TestClient
from platform_api.main import app
from platform_core.db import get_database_url
from platform_core.models import PlatformOutboxEvent, WebsiteGenerationJob
from platform_testing.db_helpers import ensure_auth_user
from platform_worker.job_runner import poll_and_execute_jobs
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"


def _token(sub: uuid.UUID, email: str) -> str:
    return jwt.encode(
        {
            "sub": str(sub),
            "email": email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


def _headers(user_id: uuid.UUID, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user_id, email)}"}


def _seed(user_id: uuid.UUID, email: str) -> None:
    async def _run() -> None:
        url = get_database_url()
        assert url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            await ensure_auth_user(session, user_id, email)
            await session.commit()
        await engine.dispose()

    asyncio.run(_run())


@pytest.fixture
def owner(monkeypatch: Any) -> tuple[dict[str, str], uuid.UUID]:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    user_id = uuid.uuid4()
    email = f"{user_id}@example.com"
    _seed(user_id, email)
    return _headers(user_id, email), user_id


def _create_business(client: TestClient, headers: dict[str, str]) -> str:
    resp = client.post(
        "/v1/platform/businesses",
        json={"display_name": f"Gen Co {uuid.uuid4().hex[:8]}", "business_type": "restaurant"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return cast(str, resp.json()["data"]["business"]["id"])


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_generation_fallback_always_produces_draft(owner: tuple[dict[str, str], uuid.UUID]) -> None:
    headers, _ = owner
    client = TestClient(app)
    business_id = _create_business(client, headers)

    # Business creation already enqueued a job; drain worker lane.
    async def _run_jobs() -> str:
        url = get_database_url()
        assert url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        status = "failed"
        async with factory() as session:
            for _ in range(5):
                await poll_and_execute_jobs(session, "test-website-worker")
            result = await session.execute(
                select(WebsiteGenerationJob)
                .where(WebsiteGenerationJob.business_id == uuid.UUID(business_id))
                .order_by(WebsiteGenerationJob.created_at.desc())
            )
            job = result.scalars().first()
            assert job is not None
            assert job.status in {"completed", "fallback_used"}
            assert job.result_version_id is not None
            outbox = await session.execute(
                select(PlatformOutboxEvent).where(
                    PlatformOutboxEvent.business_id == uuid.UUID(business_id),
                    PlatformOutboxEvent.event_type == "website.draft_generated",
                )
            )
            assert outbox.scalars().first() is not None
            status = job.status
        await engine.dispose()
        return status

    status = asyncio.run(_run_jobs())
    # Default provider unavailable → deterministic fallback
    assert status == "fallback_used"

    site = client.get(f"/v1/b/{business_id}/website", headers=headers)
    assert site.status_code == 200, site.text
    draft = site.json()["data"]["draft"]
    assert draft["generated_by"] == "deterministic_fallback"
    assert len(draft["pages"]) >= 3
    slugs = {p["slug"] for p in draft["pages"]}
    assert "home" in slugs
    assert "menu" in slugs  # restaurant page set


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_manual_generate_idempotent_while_running(
    owner: tuple[dict[str, str], uuid.UUID],
) -> None:
    headers, _ = owner
    client = TestClient(app)
    business_id = _create_business(client, headers)

    # Pending job from create still running/pending → second enqueue conflicts.
    resp = client.post(f"/v1/b/{business_id}/website/generate", json={}, headers=headers)
    # Either conflict (pending) or success if prior job already finished.
    assert resp.status_code in (200, 409), resp.text


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_fallback_unit_schema_valid() -> None:
    from platform_core.validation.website import validate_generation_payload
    from platform_core.website.fallback_generator import build_deterministic_draft

    payload = build_deterministic_draft(
        display_name="Unit Cafe",
        business_type="cafe",
        tagline="Fresh coffee",
        description="Neighborhood cafe",
    )
    validated = validate_generation_payload(payload)
    assert validated["pages"][0]["slug"] == "home"
