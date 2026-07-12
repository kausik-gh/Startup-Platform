import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.context import MembershipInfo
from platform_core.exceptions import PermissionDelegationError
from platform_core.models import (
    BusinessMembership,
    MembershipAppliedTemplate,
    MembershipPermissionGrant,
)
from platform_core.permissions import (
    ALL_PERMISSIONS,
    ROLE_PRIMARY_OWNER,
    TEMPLATES,
)
from platform_core.services.audit import AuditService


class TeamService:
    @staticmethod
    async def get_active_membership(
        session: AsyncSession, identity_id: uuid.UUID, business_id: uuid.UUID
    ) -> BusinessMembership | None:
        result = await session.execute(
            select(BusinessMembership).where(
                BusinessMembership.identity_id == identity_id,
                BusinessMembership.business_id == business_id,
                BusinessMembership.status == "active",
                BusinessMembership.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    @staticmethod
    async def list_members(
        session: AsyncSession, business_id: uuid.UUID
    ) -> list[BusinessMembership]:
        result = await session.execute(
            select(BusinessMembership).where(
                BusinessMembership.business_id == business_id,
                BusinessMembership.deleted_at.is_(None),
                BusinessMembership.status != "removed",
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def to_membership_info(m: BusinessMembership) -> MembershipInfo:
        scope = list(m.location_scope) if m.location_scope else None
        return MembershipInfo(
            id=m.id,
            business_id=m.business_id,
            identity_id=m.identity_id,
            role=m.role,
            status=m.status,
            location_scope=scope,
        )

    @staticmethod
    async def resolve_permissions(
        session: AsyncSession, membership: BusinessMembership
    ) -> frozenset[str]:
        if membership.role == ROLE_PRIMARY_OWNER:
            return frozenset[str](ALL_PERMISSIONS)

        perms: set[str] = set()
        grants = await session.execute(
            select(MembershipPermissionGrant).where(
                MembershipPermissionGrant.membership_id == membership.id
            )
        )
        for grant in grants.scalars().all():
            perms.add(grant.permission)

        templates = await session.execute(
            select(MembershipAppliedTemplate).where(
                MembershipAppliedTemplate.membership_id == membership.id
            )
        )
        for applied in templates.scalars().all():
            template_perms = TEMPLATES.get(applied.template_id, frozenset())
            perms.update(template_perms)

        return frozenset(perms)

    @staticmethod
    async def grant_permissions(
        session: AsyncSession,
        *,
        membership: BusinessMembership,
        permissions: set[str],
        granted_by: uuid.UUID,
        actor_permissions: frozenset[str],
        is_primary_owner: bool,
    ) -> None:
        if not is_primary_owner:
            excess = permissions - actor_permissions
            if excess:
                raise PermissionDelegationError(excess)

        for perm in permissions:
            session.add(
                MembershipPermissionGrant(
                    business_id=membership.business_id,
                    membership_id=membership.id,
                    permission=perm,
                    granted_by=granted_by,
                )
            )
        await session.flush()
        await AuditService.record(
            session,
            event_type="permission.granted",
            actor_identity_id=granted_by,
            actor_context="business",
            business_id=membership.business_id,
            resource_type="membership",
            resource_id=membership.id,
            action="grant_permissions",
            after_state={"permissions": sorted(permissions)},
        )

    @staticmethod
    async def invite_member(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        identity_id: uuid.UUID,
        role: str,
        invited_by: uuid.UUID,
    ) -> BusinessMembership:
        membership = BusinessMembership(
            business_id=business_id,
            identity_id=identity_id,
            role=role,
            status="pending",
            invited_at=datetime.now(timezone.utc),
        )
        session.add(membership)
        await session.flush()
        return membership

    @staticmethod
    async def activate_membership(
        session: AsyncSession, membership: BusinessMembership
    ) -> BusinessMembership:
        membership.status = "active"
        membership.activated_at = datetime.now(timezone.utc)
        await session.flush()
        return membership
