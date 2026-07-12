from fastapi import Request
from fastapi.responses import JSONResponse

from platform_core.exceptions import PlatformError


async def platform_error_handler(request: Request, exc: PlatformError) -> JSONResponse:
    correlation_id = request.headers.get("X-Correlation-Id", "")
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": detail.get("code", "UNKNOWN"),
                "message": detail.get("message", str(exc.detail)),
                "details": detail.get("details", {}),
            },
            "meta": {"correlation_id": correlation_id},
        },
        headers={"X-Correlation-Id": correlation_id} if correlation_id else None,
    )
