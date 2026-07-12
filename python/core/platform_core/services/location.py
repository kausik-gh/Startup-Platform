import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import BusinessLocation


class LocationService:
    @staticmethod
    async def list_for_business(
        session: AsyncSession, business_id: uuid.UUID
    ) -> list[BusinessLocation]:
        result = await session.execute(
            select(BusinessLocation).where(
                BusinessLocation.business_id == business_id,
                BusinessLocation.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(
        session: AsyncSession, business_id: uuid.UUID, location_id: uuid.UUID
    ) -> BusinessLocation | None:
        result = await session.execute(
            select(BusinessLocation).where(
                BusinessLocation.id == location_id,
                BusinessLocation.business_id == business_id,
                BusinessLocation.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    @staticmethod
    async def create_location(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        name: str,
        timezone: str = "UTC",
        address: dict[str, Any] | None = None,
    ) -> BusinessLocation:
        location = BusinessLocation(
            business_id=business_id,
            name=name,
            timezone=timezone,
            address=address,
            is_primary=False,
        )
        session.add(location)
        await session.flush()
        return location
