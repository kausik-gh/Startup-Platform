import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import (
    Business,
    BusinessLocation,
    BusinessMembership,
    BusinessModuleState,
    CommercialEntitlement,
)
from platform_core.permissions import PLATFORM_CORE_MODULE_IDS, ROLE_PRIMARY_OWNER
from platform_core.services.audit import AuditService
from platform_core.services.outbox import OutboxService


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "business"


class BusinessService:
    @staticmethod
    async def get_by_id(session: AsyncSession, business_id: uuid.UUID) -> Business | None:
        result = await session.execute(
            select(Business).where(Business.id == business_id, Business.deleted_at.is_(None))
        )
        return result.scalars().first()

    @staticmethod
    async def list_for_identity(session: AsyncSession, identity_id: uuid.UUID) -> list[Business]:
        result = await session.execute(
            select(Business)
            .join(BusinessMembership, BusinessMembership.business_id == Business.id)
            .where(
                BusinessMembership.identity_id == identity_id,
                BusinessMembership.status == "active",
                BusinessMembership.deleted_at.is_(None),
                Business.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_business(
        session: AsyncSession,
        *,
        identity_id: uuid.UUID,
        display_name: str,
        business_type: str | None = None,
        correlation_id: str,
    ) -> tuple[Business, BusinessLocation, BusinessMembership]:
        base_slug = slugify(display_name)
        slug = base_slug
        suffix = 1
        while await BusinessService.get_by_slug(session, slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        now = datetime.now(timezone.utc)
        business = Business(
            slug=slug,
            display_name=display_name,
            state="draft",
            primary_owner_identity_id=identity_id,
            business_type=business_type,
        )
        session.add(business)
        await session.flush()

        location = BusinessLocation(
            business_id=business.id,
            name="Primary Location",
            is_primary=True,
            timezone="UTC",
        )
        session.add(location)
        await session.flush()

        membership = BusinessMembership(
            business_id=business.id,
            identity_id=identity_id,
            role=ROLE_PRIMARY_OWNER,
            status="active",
            activated_at=now,
        )
        session.add(membership)
        await session.flush()

        for module_id in PLATFORM_CORE_MODULE_IDS:
            session.add(
                CommercialEntitlement(
                    business_id=business.id,
                    subject_type="module",
                    subject_id=module_id,
                    source="platform_core",
                    status="active",
                    granted_by=identity_id,
                    reason="Platform Core auto-grant",
                )
            )
            session.add(
                BusinessModuleState(
                    business_id=business.id,
                    module_id=module_id,
                    activation_state="active",
                    enabled_at=now,
                    activated_at=now,
                )
            )
        await session.flush()

        await OutboxService.publish(
            session,
            event_type="business.created",
            payload={"business_id": str(business.id), "slug": business.slug},
            business_id=business.id,
            correlation_id=correlation_id,
        )
        await AuditService.record(
            session,
            event_type="business.created",
            actor_identity_id=identity_id,
            actor_context="personal",
            business_id=business.id,
            resource_type="business",
            resource_id=business.id,
            action="create",
            after_state={"display_name": display_name, "slug": slug},
        )
        return business, location, membership

    @staticmethod
    async def get_by_slug(session: AsyncSession, slug: str) -> Business | None:
        result = await session.execute(
            select(Business).where(Business.slug == slug, Business.deleted_at.is_(None))
        )
        return result.scalars().first()

    @staticmethod
    async def update_business(
        session: AsyncSession,
        business: Business,
        *,
        display_name: str | None = None,
        visibility: str | None = None,
    ) -> Business:
        from platform_core.gates import assert_business_mutable

        # Distinct resource-state gate (Doc 11 §17.1 / Doc 12 §8.9 gate [9]).
        assert_business_mutable(business.state, action="update")
        if display_name is not None:
            business.display_name = display_name
        if visibility is not None:
            business.visibility = visibility
        await session.flush()
        return business
