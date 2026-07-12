from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from platform_api.db import get_db_session
from platform_api.dependencies import get_request_context
from platform_core.context import RequestContext
from platform_core.services.business import BusinessService

router = APIRouter(prefix="/v1/platform/businesses", tags=["business"])


class CreateBusinessRequest(BaseModel):
    display_name: str
    business_type: str | None = None


class BusinessResponse(BaseModel):
    id: str
    slug: str
    display_name: str
    state: str
    visibility: str


@router.post("")
async def create_business(
    body: CreateBusinessRequest,
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    business, location, membership = await BusinessService.create_business(
        session,
        identity_id=ctx.identity_id,
        display_name=body.display_name,
        business_type=body.business_type,
        correlation_id=ctx.correlation_id,
    )
    await session.commit()
    return {
        "data": {
            "business": BusinessResponse(
                id=str(business.id),
                slug=business.slug,
                display_name=business.display_name,
                state=business.state,
                visibility=business.visibility,
            ).model_dump(),
            "primary_location_id": str(location.id),
            "membership_id": str(membership.id),
        },
        "meta": {"correlation_id": ctx.correlation_id},
    }


@router.get("")
async def list_businesses(
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    businesses = await BusinessService.list_for_identity(session, ctx.identity_id)
    return {
        "data": [
            BusinessResponse(
                id=str(b.id),
                slug=b.slug,
                display_name=b.display_name,
                state=b.state,
                visibility=b.visibility,
            ).model_dump()
            for b in businesses
        ],
        "meta": {"correlation_id": ctx.correlation_id},
    }
