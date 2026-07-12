import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import ConsumerProfile, PlatformAdminGrant, PlatformIdentity


class IdentityService:
    @staticmethod
    async def get_by_supabase_id(
        session: AsyncSession, supabase_user_id: uuid.UUID
    ) -> Optional[PlatformIdentity]:
        result = await session.execute(
            select(PlatformIdentity).where(PlatformIdentity.supabase_user_id == supabase_user_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_id(
        session: AsyncSession, identity_id: uuid.UUID
    ) -> Optional[PlatformIdentity]:
        result = await session.execute(
            select(PlatformIdentity).where(PlatformIdentity.id == identity_id)
        )
        return result.scalars().first()

    @staticmethod
    async def bootstrap_identity(
        session: AsyncSession,
        supabase_user_id: uuid.UUID,
        email: str,
        display_name: str | None = None,
    ) -> PlatformIdentity:
        existing = await IdentityService.get_by_supabase_id(session, supabase_user_id)
        if existing:
            return existing

        name = display_name or email.split("@")[0]
        identity = PlatformIdentity(
            id=supabase_user_id,
            supabase_user_id=supabase_user_id,
            email=email,
            display_name=name,
        )
        session.add(identity)
        await session.flush()

        consumer = ConsumerProfile(identity_id=identity.id)
        session.add(consumer)
        await session.flush()
        return identity

    @staticmethod
    async def update_profile(
        session: AsyncSession,
        supabase_user_id: uuid.UUID,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Optional[PlatformIdentity]:
        identity = await IdentityService.get_by_supabase_id(session, supabase_user_id)
        if not identity:
            return None
        if display_name is not None:
            identity.display_name = display_name
        if avatar_url is not None:
            identity.avatar_url = avatar_url
        await session.flush()
        return identity

    @staticmethod
    async def is_super_admin(session: AsyncSession, identity_id: uuid.UUID) -> bool:
        result = await session.execute(
            select(PlatformAdminGrant).where(
                PlatformAdminGrant.identity_id == identity_id,
                PlatformAdminGrant.revoked_at.is_(None),
            )
        )
        return result.scalars().first() is not None

    # Legacy aliases for Stage 1C /me routes
    get_profile_by_auth_user_id = get_by_supabase_id

    @staticmethod
    async def create_profile(
        session: AsyncSession, auth_user_id: uuid.UUID, email: str, display_name: str
    ) -> PlatformIdentity:
        return await IdentityService.bootstrap_identity(session, auth_user_id, email, display_name)
