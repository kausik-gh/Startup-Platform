import asyncio
import os
import signal
import socket
import sys
from typing import Any

from sqlalchemy import text

from platform_core.db import create_worker_session_factory
from platform_worker.job_runner import poll_and_execute_jobs
from platform_worker.outbox_consumer import poll_and_dispatch_outbox
from platform_worker.scheduler import materialize_due_schedules

# Global flag for graceful shutdown
running = True


def handle_shutdown_signal(sig: int, frame: Any) -> None:
    global running
    print(f"\nReceived signal {sig}. Initiating graceful shutdown...")
    running = False


async def shutdown_tasks(sig: Any) -> None:
    global running
    print(f"Received signal {sig.name}. Initiating graceful shutdown...")
    running = False


async def _poll_lanes(session_factory: Any, worker_id: str) -> None:
    """Run the three worker lanes sequentially with separate sessions."""
    async with session_factory() as session:
        outbox_count = await poll_and_dispatch_outbox(session, worker_id)
        if outbox_count:
            print(f"[Worker] Processed {outbox_count} outbox events")

    async with session_factory() as session:
        schedule_count = await materialize_due_schedules(session, worker_id)
        if schedule_count:
            print(f"[Worker] Materialized {schedule_count} scheduled jobs")

    async with session_factory() as session:
        job_count = await poll_and_execute_jobs(session, worker_id)
        if job_count:
            print(f"[Worker] Processed {job_count} async jobs")


async def main() -> None:
    global running

    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_tasks(sig)))
    else:
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)

    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    print(f"Starting platform worker: {worker_id}")

    if not os.getenv("DATABASE_URL"):
        print("CRITICAL: DATABASE_URL is not configured. Worker cannot start.")
        sys.exit(1)

    try:
        engine, session_factory = create_worker_session_factory(role="service")
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        print("Worker successfully connected to the database.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize worker database session: {e}")
        sys.exit(1)

    poll_interval = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "2"))
    print(f"Worker polling every {poll_interval}s (outbox + schedules + async jobs)...")

    while running:
        try:
            await _poll_lanes(session_factory, worker_id)
        except Exception as e:
            print(f"[Worker] Poll error: {e}")
        await asyncio.sleep(poll_interval)

    print("Disposing database engine...")
    await engine.dispose()
    print("Worker shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped via KeyboardInterrupt.")
