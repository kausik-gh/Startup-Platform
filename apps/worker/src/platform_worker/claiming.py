from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

LEASE_SECONDS = 120


async def claim_outbox_batch(session: AsyncSession, worker_id: str, limit: int = 10) -> list[Any]:
    """
    Claims a batch of pending outbox events using SKIP LOCKED row-locking.
    """
    try:
        result = await session.execute(
            text("""
        UPDATE platform_outbox_events
        SET status = 'processing',
          leased_until = now() + make_interval(secs => :lease_seconds),
          leased_by = :worker_id
        WHERE id IN (
          SELECT id
          FROM platform_outbox_events
          WHERE status IN ('pending', 'failed')
            AND next_attempt_at <= now()
            AND (leased_until IS NULL OR leased_until < now())
          ORDER BY next_attempt_at
          FOR UPDATE SKIP LOCKED
          LIMIT :limit
        )
        RETURNING *
      """),
            {"worker_id": worker_id, "limit": limit, "lease_seconds": LEASE_SECONDS},
        )
        return list(result.mappings())
    except Exception as e:
        # During bootstrap, DB tables may not exist yet, catch and return empty list
        print(f"[Claiming] Outbox table check skipped or failed: {e}")
        return []


async def claim_job_batch(session: AsyncSession, worker_id: str, limit: int = 10) -> list[Any]:
    """
    Claims a batch of pending asynchronous jobs using SKIP LOCKED row-locking.
    """
    try:
        result = await session.execute(
            text("""
        UPDATE platform_async_jobs
        SET status = 'processing',
          leased_until = now() + make_interval(secs => :lease_seconds),
          leased_by = :worker_id
        WHERE id IN (
          SELECT id
          FROM platform_async_jobs
          WHERE status IN ('pending', 'failed')
            AND next_attempt_at <= now()
            AND (leased_until IS NULL OR leased_until < now())
          ORDER BY next_attempt_at
          FOR UPDATE SKIP LOCKED
          LIMIT :limit
        )
        RETURNING *
      """),
            {"worker_id": worker_id, "limit": limit, "lease_seconds": LEASE_SECONDS},
        )
        return list(result.mappings())
    except Exception as e:
        # During bootstrap, DB tables may not exist yet, catch and return empty list
        print(f"[Claiming] Async jobs table check skipped or failed: {e}")
        return []
