import asyncio
import os
import socket
import signal
import sys
from platform_core.db import create_worker_session_factory
from platform_worker.outbox_consumer import poll_and_dispatch_outbox
from platform_worker.job_runner import poll_and_execute_jobs
from platform_worker.scheduler import materialize_due_schedules

from typing import Any

# Global flag for graceful shutdown
running = True


def handle_shutdown_signal(sig: int, frame: Any) -> None:
    global running
    print(f"\nReceived signal {sig}. Initiating graceful shutdown...")
    running = False


async def main() -> None:
    global running

    # Register signal handlers for graceful shutdown
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_tasks(sig)))
    else:
        # Windows fallback for signals
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)

    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    print(f"Starting platform worker: {worker_id}")

    # Database connection pooling setup (optional fallback if DB not configured)
    session_factory = None
    if os.getenv("DATABASE_URL"):
        try:
            session_factory = create_worker_session_factory(role="service")
            print("Worker connected to database pool.")
        except Exception as e:
            print(f"Warning: Failed to initialize worker database session: {e}")

    poll_interval = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "2"))
    print(f"Worker running. Polling interval: {poll_interval}s")

    while running:
        if session_factory:
            try:
                async with session_factory() as session:
                    # Run claiming and processing concurrently
                    await asyncio.gather(
                        poll_and_dispatch_outbox(session, worker_id),
                        poll_and_execute_jobs(session, worker_id),
                        materialize_due_schedules(session, worker_id),
                    )
            except Exception as e:
                print(f"Error during poll execution: {e}")
        else:
            # Simulated execution loop for bootstrap/CI environment when DB is not running
            print("[Simulation] Worker polling outbox, async jobs, and scheduler...")
            await asyncio.sleep(0.1)  # Small sleep to prevent tight loop in testing

        # Sleep in increments to check for the 'running' flag quickly
        for _ in range(poll_interval * 10):
            if not running:
                break
            await asyncio.sleep(0.1)

    print("Worker shut down cleanly.")


async def shutdown_tasks(sig: Any) -> None:
    global running
    print(f"Received signal {sig.name}. Initiating graceful shutdown...")
    running = False


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped via KeyboardInterrupt.")
