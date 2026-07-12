import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import PlatformOutboxEvent


class OutboxService:
    @staticmethod
    async def publish(
        session: AsyncSession,
        *,
        event_type: str,
        payload: dict[str, Any],
        business_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
        causation_id: uuid.UUID | None = None,
    ) -> PlatformOutboxEvent:
        event = PlatformOutboxEvent(
            business_id=business_id,
            event_type=event_type,
            payload=payload,
            correlation_id=uuid.UUID(correlation_id) if correlation_id else None,
            causation_id=causation_id,
            status="pending",
        )
        session.add(event)
        await session.flush()
        return event
