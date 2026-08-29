"""Integration tests for async job and scheduled job worker lanes (Doc 12 §18)."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from platform_core.db import get_database_url
from platform_worker.claiming import claim_job_batch
from platform_worker.job_runner import poll_and_execute_jobs
from platform_worker.scheduler import materialize_due_schedules


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    url = get_database_url()
    if not url:
        pytest.skip("DATABASE_URL not configured")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _insert_async_job(
    session: AsyncSession,
    *,
    job_type: str = "platform.noop",
    payload: dict[str, Any] | None = None,
    max_attempts: int = 5,
    status: str = "pending",
) -> uuid.UUID:
    job_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO platform_async_jobs (
                id, job_type, payload, status, max_attempts, next_attempt_at
            )
            VALUES (
                :id,
                :job_type,
                CAST(:payload AS jsonb),
                :status,
                :max_attempts,
                now()
            )
        """),
        {
            "id": str(job_id),
            "job_type": job_type,
            "payload": __import__("json").dumps(payload or {}),
            "status": status,
            "max_attempts": max_attempts,
        },
    )
    await session.commit()
    return job_id


async def _job_status(session: AsyncSession, job_id: uuid.UUID) -> tuple[str, int, str | None]:
    session.expire_all()
    result = await session.execute(
        text("""
            SELECT status, attempt_count, last_error
            FROM platform_async_jobs
            WHERE id = :id
        """),
        {"id": str(job_id)},
    )
    row = result.one()
    return str(row.status), int(row.attempt_count), row.last_error


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
async def test_async_job_claim_and_completion(db_session: AsyncSession) -> None:
    job_id = await _insert_async_job(db_session, job_type="platform.noop", payload={"ok": True})

    count = await poll_and_execute_jobs(db_session, "test-job-worker")
    assert count >= 1

    status, attempt_count, last_error = await _job_status(db_session, job_id)
    assert status == "completed"
    assert attempt_count == 0
    assert last_error is None

    processed = await db_session.execute(
        text("""
            SELECT handler FROM platform_processed_events
            WHERE event_id = :id AND handler = 'job_runner.platform.noop'
        """),
        {"id": str(job_id)},
    )
    assert processed.first() is not None


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
async def test_async_job_retry_on_failure(db_session: AsyncSession) -> None:
    job_id = await _insert_async_job(
        db_session,
        job_type="platform.noop",
        payload={"__force_fail": True, "__force_fail_message": "transient failure"},
        max_attempts=5,
    )

    count = await poll_and_execute_jobs(db_session, "test-job-retry")
    assert count == 0

    status, attempt_count, last_error = await _job_status(db_session, job_id)
    assert status == "failed"
    assert attempt_count == 1
    assert last_error is not None
    assert "transient failure" in last_error

    # Not yet due because of backoff
    claimed = await claim_job_batch(db_session, "test-job-retry-2")
    claimed_ids = {str(row["id"]) for row in claimed}
    assert str(job_id) not in claimed_ids
    await db_session.rollback()

    # Make retry due immediately
    await db_session.execute(
        text("UPDATE platform_async_jobs SET next_attempt_at = now() WHERE id = :id"),
        {"id": str(job_id)},
    )
    await db_session.commit()

    # Still forced to fail — second attempt
    await poll_and_execute_jobs(db_session, "test-job-retry-3")
    status, attempt_count, _ = await _job_status(db_session, job_id)
    assert status == "failed"
    assert attempt_count == 2


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
async def test_async_job_dead_letter_on_max_attempts(db_session: AsyncSession) -> None:
    job_id = await _insert_async_job(
        db_session,
        job_type="platform.noop",
        payload={"__force_fail": True, "__force_fail_message": "terminal failure"},
        max_attempts=1,
    )

    await poll_and_execute_jobs(db_session, "test-job-dlq")
    status, attempt_count, last_error = await _job_status(db_session, job_id)
    assert status == "dead_letter"
    assert attempt_count == 1
    assert last_error is not None

    dlq = await db_session.execute(
        text("""
            SELECT source_table, event_type, final_error, attempt_count
            FROM platform_dead_letter_events
            WHERE source_id = :id AND source_table = 'platform_async_jobs'
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"id": str(job_id)},
    )
    row = dlq.one()
    assert row.source_table == "platform_async_jobs"
    assert row.event_type == "platform.noop"
    assert "terminal failure" in row.final_error
    assert int(row.attempt_count) == 1


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
async def test_scheduled_job_materialization(db_session: AsyncSession) -> None:
    schedule_id = uuid.uuid4()
    await db_session.execute(
        text("""
            INSERT INTO platform_scheduled_jobs (
                id, schedule_type, payload, run_at, status
            )
            VALUES (
                :id,
                'platform.noop',
                '{"source": "schedule"}'::jsonb,
                now() - interval '1 second',
                'pending'
            )
        """),
        {"id": str(schedule_id)},
    )
    await db_session.commit()

    count = await materialize_due_schedules(db_session, "test-scheduler")
    assert count >= 1

    db_session.expire_all()
    schedule = await db_session.execute(
        text("""
            SELECT status, materialized_job_id
            FROM platform_scheduled_jobs
            WHERE id = :id
        """),
        {"id": str(schedule_id)},
    )
    srow = schedule.one()
    assert srow.status == "materialized"
    assert srow.materialized_job_id is not None

    job = await db_session.execute(
        text("""
            SELECT job_type, status, causation_id, payload
            FROM platform_async_jobs
            WHERE id = :id
        """),
        {"id": str(srow.materialized_job_id)},
    )
    jrow = job.one()
    assert jrow.job_type == "platform.noop"
    assert jrow.status == "pending"
    assert str(jrow.causation_id) == str(schedule_id)

    # Materializing again must not duplicate
    again = await materialize_due_schedules(db_session, "test-scheduler")
    assert again == 0

    # Execute the materialized job
    executed = await poll_and_execute_jobs(db_session, "test-scheduler-exec")
    assert executed >= 1
    status, _, _ = await _job_status(db_session, srow.materialized_job_id)
    assert status == "completed"


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
async def test_concurrent_job_claim_safety(db_session: AsyncSession) -> None:
    job_id = await _insert_async_job(db_session, job_type="platform.noop")

    url = get_database_url()
    assert url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session_a, factory() as session_b:
        claimed_a = await claim_job_batch(session_a, "worker-a", limit=10)
        claimed_b = await claim_job_batch(session_b, "worker-b", limit=10)
        await session_a.commit()
        await session_b.commit()

    await engine.dispose()

    ids_a = {str(row["id"]) for row in claimed_a}
    ids_b = {str(row["id"]) for row in claimed_b}
    # The specific job must be claimed by at most one worker
    assert not (str(job_id) in ids_a and str(job_id) in ids_b)
    assert str(job_id) in ids_a or str(job_id) in ids_b
