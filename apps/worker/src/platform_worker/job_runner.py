from sqlalchemy.ext.asyncio import AsyncSession
from platform_worker.claiming import claim_job_batch


async def poll_and_execute_jobs(session: AsyncSession, worker_id: str) -> None:
    """
    Polls async jobs from platform_async_jobs and executes their payloads.
    """
    jobs = await claim_job_batch(session, worker_id)
    if not jobs:
        return

    print(f"[JobRunner] Claimed {len(jobs)} jobs to execute.")
    for job in jobs:
        # Under Stage 1A, we only log the claim. Handlers will be defined in later stages.
        print(f"[JobRunner] Executing job: {job.get('id')} of type: {job.get('job_type')}")
