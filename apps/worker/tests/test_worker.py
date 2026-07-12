import pytest
import asyncio
from platform_worker.main import main
from typing import Any


@pytest.mark.asyncio
async def test_worker_shutdown_behavior(monkeypatch: Any) -> None:
    # Set running = False to ensure the worker main loop terminates instantly
    monkeypatch.setattr("platform_worker.main.running", False)

    # Run worker main. It should exit cleanly immediately without polling since running is False.
    # We wrap it in a timeout just in case it hangs
    try:
        await asyncio.wait_for(main(), timeout=1.0)
        assert True
    except asyncio.TimeoutError:
        pytest.fail("Worker loop hung and failed to exit gracefully.")
