import uuid
from uuid import uuid4

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.context import (
    EntitlementSet,
    ModuleStateInfo,
    OperatingContext,
    RequestContext,
)
from platform_core.exceptions import (
    LocationAccessDenied,
    MembershipRequired,
    ResourceNotFound,
)
from platform_core.services.business import BusinessService
from platform_core.services.entitlement import EntitlementService, ModuleService
from platform_core.services.identity import IdentityService
from platform_core.services.team import TeamService


def _parse_business_context(
    request: Request,
) -> tuple[OperatingContext, uuid.UUID | None, uuid.UUID | None]:
    """Resolve operating context from path params and headers."""
    path = request.url.path
    if path.startswith("/v1/admin"):
        return OperatingContext.ADMIN, None, None

    business_id_str = request.path_params.get("business_id")
    if business_id_str:
        try:
            business_id = uuid.UUID(str(business_id_str))
            location_id_str = request.headers.get("X-Location-Id")
            location_id = uuid.UUID(location_id_str) if location_id_str else None
            return OperatingContext.BUSINESS, business_id, location_id
        except ValueError:
            pass

    ctx_header = request.headers.get("X-Operating-Context", "personal").lower()
    business_id_str = request.headers.get("X-Business-Id")
    location_id_str = request.headers.get("X-Location-Id")

    if ctx_header == "business" and business_id_str:
        try:
            business_id = uuid.UUID(business_id_str)
            location_id = uuid.UUID(location_id_str) if location_id_str else None
            return OperatingContext.BUSINESS, business_id, location_id
        except ValueError:
            pass
    if ctx_header == "admin":
        return OperatingContext.ADMIN, None, None
    return OperatingContext.PERSONAL, None, None


async def bind_session_context(
    session: AsyncSession,
    identity_id: uuid.UUID,
    business_id: uuid.UUID | None,
) -> None:
    await session.execute(
        text("SELECT set_config('app.current_identity_id', :iid, true)"),
        {"iid": str(identity_id)},
    )
    if business_id:
        await session.execute(
            text("SELECT set_config('app.current_business_id', :bid, true)"),
            {"bid": str(business_id)},
        )


async def resolve_request_context(
    request: Request,
    session: AsyncSession,
    *,
    supabase_user_id: uuid.UUID,
    email: str,
    correlation_id: str | None = None,
) -> RequestContext:
    identity = await IdentityService.bootstrap_identity(session, supabase_user_id, email)
    await session.flush()

    active_context, business_id, location_id = _parse_business_context(request)
    membership_info = None
    effective_permissions: frozenset[str] = frozenset()
    effective_entitlements = EntitlementSet()
    module_states: dict[str, ModuleStateInfo] = {}

    is_super_admin = await IdentityService.is_super_admin(session, identity.id)

    if active_context == OperatingContext.BUSINESS:
        if business_id is None:
            raise MembershipRequired()
        business = await BusinessService.get_by_id(session, business_id)
        if not business:
            raise ResourceNotFound("Business")

        membership = await TeamService.get_active_membership(session, identity.id, business_id)
        if not membership:
            raise MembershipRequired()

        membership_info = TeamService.to_membership_info(membership)
        if location_id and not membership_info.allows_location(location_id):
            raise LocationAccessDenied()

        effective_permissions = await TeamService.resolve_permissions(session, membership)
        effective_entitlements = await EntitlementService.get_effective(session, business_id)
        raw_states = await ModuleService.get_states(session, business_id)
        module_states = {
            mid: ModuleStateInfo(
                module_id=mid,
                activation_state=s.activation_state,
                configuration=s.configuration,
            )
            for mid, s in raw_states.items()
        }
        await bind_session_context(session, identity.id, business_id)
    else:
        await bind_session_context(session, identity.id, None)

    return RequestContext(
        identity_id=identity.id,
        supabase_user_id=supabase_user_id,
        email=email,
        display_name=identity.display_name,
        active_context=active_context,
        business_id=business_id,
        location_id=location_id,
        membership=membership_info,
        effective_permissions=effective_permissions,
        effective_entitlements=effective_entitlements,
        module_states=module_states,
        is_super_admin=is_super_admin,
        correlation_id=correlation_id or request.headers.get("X-Correlation-Id") or str(uuid4()),
    )
