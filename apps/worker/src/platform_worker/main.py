import asyncio
import os
import socket
import signal
import sys
from platform_core.db import create_worker_session_factory
from sqlalchemy import text
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

    if not os.getenv("DATABASE_URL"):
        print("CRITICAL: DATABASE_URL is not configured. Worker cannot start.")
        sys.exit(1)

    try:
        engine, session_factory = create_worker_session_factory(role="service")

        # Verify connectivity
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))

        print("Worker successfully connected to the database.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize worker database session: {e}")
        sys.exit(1)

    print("Worker foundation ready. Waiting for Stage 1 slices for job execution...")

    # Wait until shutdown signal
    while running:
        await asyncio.sleep(1)

    print("Disposing database engine...")
    await engine.dispose()
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
