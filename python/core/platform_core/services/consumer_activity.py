"""Consumer activity projection writer (Doc 12 §5.13).

Stage 5 writes projection rows so Stage 7 My Activity UI has data.
Does NOT build My Activity UI (Doc 11 §17.7).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.models import ConsumerActivityProjection, CustomerContact


class ConsumerActivityService:
    @staticmethod
    async def record(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        identity_id: uuid.UUID | None,
        activity_type: str,
        resource_type: str,
        resource_id: uuid.UUID,
        summary: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> ConsumerActivityProjection | None:
        if identity_id is None:
            return None
        existing = (
            await session.execute(
                select(ConsumerActivityProjection).where(
                    ConsumerActivityProjection.identity_id == identity_id,
                    ConsumerActivityProjection.resource_type == resource_type,
                    ConsumerActivityProjection.resource_id == resource_id,
                    ConsumerActivityProjection.activity_type == activity_type,
                )
            )
        ).scalars().first()
        if existing is not None:
            existing.summary = summary or {}
            existing.occurred_at = occurred_at or datetime.now(timezone.utc)
            await session.flush()
            return existing
        row = ConsumerActivityProjection(
            identity_id=identity_id,
            business_id=business_id,
            activity_type=activity_type,
            resource_type=resource_type,
            resource_id=resource_id,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            summary=summary or {},
        )
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def record_for_customer_contact(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        customer_contact_id: uuid.UUID | None,
        activity_type: str,
        resource_type: str,
        resource_id: uuid.UUID,
        summary: dict[str, Any] | None = None,
    ) -> ConsumerActivityProjection | None:
        if customer_contact_id is None:
            return None
        contact = (
            await session.execute(
                select(CustomerContact).where(
                    CustomerContact.id == customer_contact_id,
                    CustomerContact.business_id == business_id,
                )
            )
        ).scalars().first()
        if contact is None or contact.identity_id is None:
            return None
        return await ConsumerActivityService.record(
            session,
            business_id=business_id,
            identity_id=contact.identity_id,
            activity_type=activity_type,
            resource_type=resource_type,
            resource_id=resource_id,
            summary=summary,
        )
