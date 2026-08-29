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
    ValidationError,
)
from platform_core.models import PlatformIdentity
from platform_core.services.business import BusinessService
from platform_core.services.entitlement import EntitlementService, ModuleService
from platform_core.services.identity import IdentityService
from platform_core.services.team import TeamService


def _parse_optional_uuid(value: str | None, *, field: str) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid UUID for {field}",
            details={"errors": [{"field": field, "message": f"Malformed UUID: {value}"}]},
        ) from exc


def _parse_business_context(
    request: Request,
) -> tuple[OperatingContext, uuid.UUID | None, uuid.UUID | None]:
    """Resolve operating context from path params and headers."""
    path = request.url.path
    if path.startswith("/v1/admin"):
        return OperatingContext.ADMIN, None, None

    business_id_str = request.path_params.get("business_id")
    if business_id_str:
        business_id = _parse_optional_uuid(str(business_id_str), field="business_id")
        location_id = _parse_optional_uuid(
            request.headers.get("X-Location-Id"), field="X-Location-Id"
        )
        return OperatingContext.BUSINESS, business_id, location_id

    ctx_header = request.headers.get("X-Operating-Context", "personal").lower()
    header_business_id = request.headers.get("X-Business-Id")
    header_location_id = request.headers.get("X-Location-Id")

    if ctx_header == "business":
        resolved_business_id = _parse_optional_uuid(header_business_id, field="X-Business-Id")
        resolved_location_id = _parse_optional_uuid(header_location_id, field="X-Location-Id")
        # business_id may be filled from default/last later
        return OperatingContext.BUSINESS, resolved_business_id, resolved_location_id
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


def _empty_personal_context(
    *,
    identity: PlatformIdentity,
    supabase_user_id: uuid.UUID,
    email: str,
    is_super_admin: bool,
    correlation_id: str | None,
    request: Request,
) -> RequestContext:
    return RequestContext(
        identity_id=identity.id,
        supabase_user_id=supabase_user_id,
        email=email,
        display_name=identity.display_name,
        active_context=OperatingContext.PERSONAL,
        business_id=None,
        location_id=None,
        membership=None,
        effective_permissions=frozenset(),
        effective_entitlements=EntitlementSet(),
        module_states={},
        is_super_admin=is_super_admin,
        correlation_id=correlation_id or request.headers.get("X-Correlation-Id") or str(uuid4()),
    )


async def resolve_request_context(
    request: Request,
    session: AsyncSession,
    *,
    supabase_user_id: uuid.UUID,
    email: str,
    correlation_id: str | None = None,
    force_personal: bool = False,
) -> RequestContext:
    identity = await IdentityService.bootstrap_identity(session, supabase_user_id, email)
    await session.flush()

    active_context, business_id, location_id = _parse_business_context(request)
    membership_info = None
    effective_permissions: frozenset[str] = frozenset()
    effective_entitlements = EntitlementSet()
    module_states: dict[str, ModuleStateInfo] = {}

    is_super_admin = await IdentityService.is_super_admin(session, identity.id)

    if force_personal:
        # Identity-only context for endpoints that must run before a membership
        # exists — invitation accept/decline. Doc 12 §8.9 gate [4] cannot apply
        # to the request that creates the membership it would check; those
        # handlers authorise on the invitation recipient match instead.
        await bind_session_context(session, identity.id, None)
        return _empty_personal_context(
            identity=identity,
            supabase_user_id=supabase_user_id,
            email=email,
            is_super_admin=is_super_admin,
            correlation_id=correlation_id,
            request=request,
        )
    explicit_business_header = request.headers.get("X-Business-Id") is not None
    path_business = request.path_params.get("business_id") is not None
    restored_preference = False

    if active_context == OperatingContext.BUSINESS and business_id is None:
        # Stage 2B restore: default → last → no business context (do not guess).
        remembered = await IdentityService.get_remembered_business_id(session, identity.id)
        if remembered is not None:
            business_id = remembered
            restored_preference = True
        else:
            await bind_session_context(session, identity.id, None)
            return _empty_personal_context(
                identity=identity,
                supabase_user_id=supabase_user_id,
                email=email,
                is_super_admin=is_super_admin,
                correlation_id=correlation_id,
                request=request,
            )

    if active_context == OperatingContext.BUSINESS:
        if business_id is None:
            raise MembershipRequired()
        business = await BusinessService.get_by_id(session, business_id)
        if not business:
            if path_business or explicit_business_header:
                raise ResourceNotFound("Business")
            await bind_session_context(session, identity.id, None)
            return _empty_personal_context(
                identity=identity,
                supabase_user_id=supabase_user_id,
                email=email,
                is_super_admin=is_super_admin,
                correlation_id=correlation_id,
                request=request,
            )

        membership = await TeamService.get_membership(session, identity.id, business_id)
        if membership is None or membership.status != "active":
            if path_business or explicit_business_header:
                raise MembershipRequired()
            # Restored preference no longer valid → no business context.
            await bind_session_context(session, identity.id, None)
            return _empty_personal_context(
                identity=identity,
                supabase_user_id=supabase_user_id,
                email=email,
                is_super_admin=is_super_admin,
                correlation_id=correlation_id,
                request=request,
            )

        # Restored closed default/last → no business context (do not guess another).
        if restored_preference and business.state == "closed":
            await bind_session_context(session, identity.id, None)
            return _empty_personal_context(
                identity=identity,
                supabase_user_id=supabase_user_id,
                email=email,
                is_super_admin=is_super_admin,
                correlation_id=correlation_id,
                request=request,
            )

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
