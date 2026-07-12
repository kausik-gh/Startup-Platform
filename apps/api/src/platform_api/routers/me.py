from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from platform_api.auth import get_current_user, RequestContext
from platform_api.db import get_db_session
from platform_core.services.identity import IdentityService

router = APIRouter(prefix="/me", tags=["identity"])


class ProfileResponse(BaseModel):
    id: str
    auth_user_id: str
    email: str
    display_name: str
    avatar_url: str | None


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None


@router.get("", response_model=ProfileResponse)
async def get_me(
    context: RequestContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    profile = await IdentityService.get_profile_by_auth_user_id(session, context.auth_user_id)

    # Profile Bootstrap
    if not profile:
        # Create it automatically
        # Extract a sensible display name from email if needed
        display_name = context.email.split("@")[0]
        profile = await IdentityService.create_profile(
            session,
            auth_user_id=context.auth_user_id,
            email=context.email,
            display_name=display_name,
        )
        await session.commit()
        await session.refresh(profile)

    return ProfileResponse(
        id=str(profile.id),
        auth_user_id=str(profile.auth_user_id),
        email=profile.email,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
    )


@router.patch("", response_model=ProfileResponse)
async def update_me(
    update_data: ProfileUpdateRequest,
    context: RequestContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    profile = await IdentityService.update_profile(
        session,
        auth_user_id=context.auth_user_id,
        display_name=update_data.display_name,
        avatar_url=update_data.avatar_url,
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await session.commit()
    await session.refresh(profile)

    return ProfileResponse(
        id=str(profile.id),
        auth_user_id=str(profile.auth_user_id),
        email=profile.email,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
    )
