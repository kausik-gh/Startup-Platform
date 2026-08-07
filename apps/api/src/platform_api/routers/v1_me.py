from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from platform_api.db import get_db_session
from platform_api.dependencies import get_request_context
from platform_core.context import RequestContext
from platform_core.services.identity import IdentityService

router = APIRouter(prefix="/v1/me", tags=["identity"])


class ProfileResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    avatar_url: str | None


class ContextResponse(BaseModel):
    identity_id: str
    active_context: str
    business_id: str | None
    location_id: str | None
    is_super_admin: bool
    permissions: list[str]
    entitled_modules: list[str]
    module_states: dict[str, str]
    default_business_id: str | None = None
    last_business_id: str | None = None
    primary_business_id: str | None = None


@router.get("")
async def get_me_v1(
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    identity = await IdentityService.get_by_id(session, ctx.identity_id)
    await session.commit()
    return {
        "data": ProfileResponse(
            id=str(ctx.identity_id),
            email=ctx.email,
            display_name=identity.display_name if identity else ctx.display_name,
            avatar_url=identity.avatar_url if identity else None,
        ).model_dump(),
        "meta": {"correlation_id": ctx.correlation_id},
    }


@router.get("/context")
async def get_context(
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    prefs = await IdentityService.get_consumer_preferences(session, ctx.identity_id)
    return {
        "data": ContextResponse(
            identity_id=str(ctx.identity_id),
            active_context=ctx.active_context.value,
            business_id=str(ctx.business_id) if ctx.business_id else None,
            location_id=str(ctx.location_id) if ctx.location_id else None,
            is_super_admin=ctx.is_super_admin,
            permissions=sorted(ctx.effective_permissions),
            entitled_modules=sorted(ctx.effective_entitlements.modules),
            module_states={k: v.activation_state for k, v in ctx.module_states.items()},
            default_business_id=prefs.get("default_business_id"),
            last_business_id=prefs.get("last_business_id"),
            primary_business_id=prefs.get("primary_business_id"),
        ).model_dump(),
        "meta": {"correlation_id": ctx.correlation_id},
    }
