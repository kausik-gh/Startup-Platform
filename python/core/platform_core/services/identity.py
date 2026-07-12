import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import PlatformProfile


class IdentityService:
    @staticmethod
    async def get_profile_by_auth_user_id(
        session: AsyncSession, auth_user_id: uuid.UUID
    ) -> Optional[PlatformProfile]:
        result = await session.execute(
            select(PlatformProfile).where(PlatformProfile.auth_user_id == auth_user_id)
        )
        return result.scalars().first()

    @staticmethod
    async def create_profile(
        session: AsyncSession, auth_user_id: uuid.UUID, email: str, display_name: str
    ) -> PlatformProfile:
        profile = PlatformProfile(
            auth_user_id=auth_user_id,
            email=email,
            display_name=display_name,
        )
        session.add(profile)
        await session.flush()
        return profile

    @staticmethod
    async def update_profile(
        session: AsyncSession,
        auth_user_id: uuid.UUID,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Optional[PlatformProfile]:
        profile = await IdentityService.get_profile_by_auth_user_id(session, auth_user_id)
        if not profile:
            return None

        if display_name is not None:
            profile.display_name = display_name
        if avatar_url is not None:
            profile.avatar_url = avatar_url

        await session.flush()
        return profile
