import os
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from platform_api.db import get_db_session
from platform_core.context import RequestContext
from platform_core.context_resolver import resolve_request_context
from platform_core.exceptions import (
    AuthenticationRequired,
    EntitlementRequired,
    LocationAccessDenied,
    MembershipRequired,
    ModuleNotActive,
    PermissionDenied,
    ResourceNotFound,
    SessionExpired,
)
from platform_core.models import Business, BusinessMembership
from platform_core.services.business import BusinessService
from platform_core.services.team import TeamService


security = HTTPBearer(auto_error=False)

ContextDependency = Callable[..., Coroutine[Any, Any, RequestContext]]


@dataclass(frozen=True)
class BusinessActorContext:
    request: RequestContext
    business: Business
    actor_membership: BusinessMembership


async def resolve_business_actor(
    business_id: uuid.UUID,
    permission: str,
    ctx: RequestContext,
    session: AsyncSession,
) -> BusinessActorContext:
    """Resolve active membership and permission against a path business_id."""
    from platform_core.authorization.resolver import AuthorizationService

    business = await BusinessService.get_by_id(session, business_id)
    if not business:
        raise ResourceNotFound("Business")
    membership = await TeamService.get_active_membership(session, ctx.identity_id, business_id)
    if membership is None:
        raise MembershipRequired()
    decision = await AuthorizationService.authorize(
        session,
        business_id=business_id,
        identity_id=ctx.identity_id,
        permission=permission,
    )
    if not decision.allowed:
        raise PermissionDenied(permission)
    return BusinessActorContext(request=ctx, business=business, actor_membership=membership)


def require_business_actor(permission: str) -> Callable[..., Coroutine[Any, Any, BusinessActorContext]]:
    async def check(
        business_id: uuid.UUID,
        ctx: RequestContext = Depends(get_request_context),
        session: AsyncSession = Depends(get_db_session),
    ) -> BusinessActorContext:
        return await resolve_business_actor(business_id, permission, ctx, session)

    return check


async def verify_jwt_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None:
        raise AuthenticationRequired()
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")
    import jwt

    try:
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        if not payload.get("sub") or not payload.get("email"):
            raise AuthenticationRequired("Invalid token payload")
        return payload
    except jwt.ExpiredSignatureError:
        raise SessionExpired()
    except jwt.InvalidTokenError:
        raise AuthenticationRequired("Invalid token")


async def get_request_context(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    jwt_payload: dict[str, Any] = Depends(verify_jwt_payload),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
) -> RequestContext:
    return await resolve_request_context(
        request,
        session,
        supabase_user_id=uuid.UUID(jwt_payload["sub"]),
        email=jwt_payload["email"],
        correlation_id=x_correlation_id,
    )


def require_permission(permission: str) -> ContextDependency:
    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if permission not in ctx.effective_permissions:
            raise PermissionDenied(permission)
        return ctx

    return check


def require_entitlement(module_id: str) -> ContextDependency:
    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if not ctx.effective_entitlements.is_entitled(module_id):
            raise EntitlementRequired(module_id)
        return ctx

    return check


def require_active_module(module_id: str) -> ContextDependency:
    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        state = ctx.module_states.get(module_id)
        if state is None or not state.is_operational():
            raise ModuleNotActive(module_id)
        return ctx

    return check


def require_business_membership() -> ContextDependency:
    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if ctx.membership is None or ctx.business_id is None:
            raise MembershipRequired()
        return ctx

    return check


def require_location_access() -> ContextDependency:
    """Location scope gate — distinct from permission / entitlement / module / resource."""

    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if ctx.membership is None:
            raise MembershipRequired()
        if ctx.location_id is not None and not ctx.membership.allows_location(ctx.location_id):
            raise LocationAccessDenied()
        return ctx

    return check


def require_super_admin() -> ContextDependency:
    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if not ctx.is_super_admin:
            raise PermissionDenied("admin.access")
        return ctx

    return check
