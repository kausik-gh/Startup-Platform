from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from platform_api.db import get_db_session
from platform_api.dependencies import require_super_admin
from platform_core.context import RequestContext
from platform_core.exceptions import ResourceNotFound
from platform_core.services.audit import AuditService
from platform_core.services.business import BusinessService

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/businesses/{business_id}")
async def admin_get_business(
    business_id: UUID,
    ctx: RequestContext = Depends(require_super_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    business = await BusinessService.get_by_id(session, business_id)
    if not business:
        raise ResourceNotFound("Business")

    await AuditService.record(
        session,
        event_type="admin.business.inspected",
        actor_identity_id=ctx.identity_id,
        actor_context="admin",
        business_id=business_id,
        resource_type="business",
        resource_id=business_id,
        action="inspect",
        after_state={"display_name": business.display_name, "state": business.state},
    )
    await session.commit()

    return {
        "data": {
            "id": str(business.id),
            "slug": business.slug,
            "display_name": business.display_name,
            "state": business.state,
            "visibility": business.visibility,
        },
        "meta": {"correlation_id": ctx.correlation_id},
    }
