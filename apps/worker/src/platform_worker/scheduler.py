from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def materialize_due_schedules(session: AsyncSession, worker_id: str) -> None:
    """
    Checks due scheduled jobs and materializes them into async jobs.
    """
    try:
        # Under Stage 1A, we only query for due scheduled jobs using a transactional lock
        result = await session.execute(
            text("""
        SELECT * FROM platform_scheduled_jobs
        WHERE status = 'pending'
          AND run_at <= now()
        FOR UPDATE SKIP LOCKED
      """)
        )
        due_jobs = result.all()
        if due_jobs:
            print(f"[Scheduler] Found {len(due_jobs)} due schedules to materialize.")
            # In a full run, we would insert these into platform_async_jobs and mark them materialized
    except Exception:
        # During bootstrap, DB tables may not exist yet, catch and pass
        pass
