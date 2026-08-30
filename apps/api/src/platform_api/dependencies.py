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


def assert_entitled(ctx: RequestContext, module_id: str) -> None:
    """Gate [6] — Commercial Entitlement (Doc 12 SS8.9)."""
    if not ctx.effective_entitlements.is_entitled(module_id):
        raise EntitlementRequired(module_id)


def assert_module_operational(ctx: RequestContext, module_id: str) -> None:
    """Gate [7] — module enabled + configured + applicable (Doc 12 SS8.9)."""
    state = ctx.module_states.get(module_id)
    if state is None or not state.is_operational():
        raise ModuleNotActive(module_id)


async def resolve_business_actor(
    business_id: uuid.UUID,
    permission: str,
    ctx: RequestContext,
    session: AsyncSession,
    module_id: str | None = None,
) -> BusinessActorContext:
    """Resolve active membership and permission against a path business_id.

    Runs the Doc 12 SS8.9 gate chain in canonical order: [3] Business exists ->
    [4] membership active -> [6] Entitlement -> [7] module state -> [8] permission.
    `module_id` is supplied only for genuine optional modules; Platform Core
    groups are auto-granted and auto-activated at Business creation and are
    deliberately outside the optional-module Entitlement/activation path.
    """
    from platform_core.authorization.resolver import AuthorizationService
    from platform_core.context_resolver import bind_session_context

    business = await BusinessService.get_by_id(session, business_id)
    if not business:
        raise ResourceNotFound("Business")
    membership = await TeamService.get_active_membership(session, ctx.identity_id, business_id)
    if membership is None:
        raise MembershipRequired()

    # RLS (AUD-02): the request context's GUC was bound from the X-Business-Id
    # header, which most callers don't send — they carry the business in the
    # path. Now that gates [3] and [4] have confirmed this identity is an active
    # member, bind `app.current_business_id` from the verified path value so the
    # handler's tenant-scoped queries resolve. Binding earlier, from the
    # unverified path param, would let a non-member read the row.
    await bind_session_context(session, ctx.identity_id, business_id)

    if module_id is not None:
        assert_entitled(ctx, module_id)
        assert_module_operational(ctx, module_id)
    decision = await AuthorizationService.authorize(
        session,
        business_id=business_id,
        identity_id=ctx.identity_id,
        permission=permission,
    )
    if not decision.allowed:
        raise PermissionDenied(permission)
    return BusinessActorContext(request=ctx, business=business, actor_membership=membership)


def require_business_actor(
    permission: str, module_id: str | None = None
) -> Callable[..., Coroutine[Any, Any, BusinessActorContext]]:
    async def check(
        business_id: uuid.UUID,
        ctx: RequestContext = Depends(get_request_context),
        session: AsyncSession = Depends(get_db_session),
    ) -> BusinessActorContext:
        return await resolve_business_actor(business_id, permission, ctx, session, module_id)

    return check


async def resolve_business_member(
    business_id: uuid.UUID,
    ctx: RequestContext,
    session: AsyncSession,
) -> BusinessActorContext:
    """Gate chain [3] Business exists -> [4] membership active, and STOP.

    Deliberately omits gate [8] permission. Use ONLY for endpoints whose entire
    result set is the calling identity's own personal data, where the identity
    scope is applied by the handler itself and no path/query parameter can widen
    it (Core Notifications inbox: list, unread-count, mark-read, mark-all-read).

    A member must be able to read notifications addressed to them — an invitee
    or a lead assignee holds no explicit grants at the moment their notification
    is created, and AUD-07 (manager/member roles carry no default permissions)
    means role defaults will not supply one. Gating a personal inbox behind a
    delegated permission makes those notifications structurally undeliverable.
    What *reaches* an inbox is still permission-gated per resource at fan-out
    (NotificationService.resolve_recipients), so this does not widen access to
    Business data. Anything reading another identity's data keeps gate [8].
    """
    from platform_core.context_resolver import bind_session_context

    business = await BusinessService.get_by_id(session, business_id)
    if not business:
        raise ResourceNotFound("Business")
    membership = await TeamService.get_active_membership(session, ctx.identity_id, business_id)
    if membership is None:
        raise MembershipRequired()
    # RLS: bind the verified business scope from the path (see resolve_business_actor).
    await bind_session_context(session, ctx.identity_id, business_id)
    return BusinessActorContext(request=ctx, business=business, actor_membership=membership)


def require_business_member() -> Callable[..., Coroutine[Any, Any, BusinessActorContext]]:
    """Membership-only dependency — see `resolve_business_member` for the rules."""

    async def check(
        business_id: uuid.UUID,
        ctx: RequestContext = Depends(get_request_context),
        session: AsyncSession = Depends(get_db_session),
    ) -> BusinessActorContext:
        return await resolve_business_member(business_id, ctx, session)

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


async def get_identity_context(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    jwt_payload: dict[str, Any] = Depends(verify_jwt_payload),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
) -> RequestContext:
    """Identity-only context for endpoints that precede membership creation
    (invitation accept/decline). Skips gate [4]; the handler authorises on the
    invitation recipient match instead."""
    return await resolve_request_context(
        request,
        session,
        supabase_user_id=uuid.UUID(jwt_payload["sub"]),
        email=jwt_payload["email"],
        correlation_id=x_correlation_id,
        force_personal=True,
    )


def require_permission(permission: str) -> ContextDependency:
    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if permission not in ctx.effective_permissions:
            raise PermissionDenied(permission)
        return ctx

    return check


def require_entitlement(module_id: str) -> ContextDependency:
    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        assert_entitled(ctx, module_id)
        return ctx

    return check


def require_active_module(module_id: str) -> ContextDependency:
    async def check(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        assert_module_operational(ctx, module_id)
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
