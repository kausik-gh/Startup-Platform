"""Shared pytest setup for the apps/api suite.

Rate limiting is disabled for the whole test session. `RateLimitMiddleware`
keeps its sliding windows keyed by client IP, and every `TestClient(app)`
request arrives from the same synthetic host, so a test file that creates many
businesses / payments / bookings in quick succession would trip the shared
buckets and fail for reasons that have nothing to do with what it is testing.

The rate limiter has its own dedicated coverage in `test_rate_limiting.py`,
which re-enables it explicitly.

This must run before any test module executes `from platform_api.main import
app`, because the middleware reads the flag at import time. conftest.py is
imported by pytest before test collection, so it does.
"""

import os

os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
