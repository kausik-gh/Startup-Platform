"""Merchant connection service (Stage 9)."""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.gates import assert_business_mutable
from platform_core.models import MerchantConnection
from platform_core.resolvers.payment_resolver import PaymentResolver
from platform_core.services.audit import AuditService
from platform_core.services.business import BusinessService
from platform_core.services.outbox import OutboxService
from platform_core.validation.payment import validate_merchant_update_payload


class MerchantService:
    @staticmethod
    def serialize(connection: MerchantConnection) -> dict[str, Any]:
        return cast(dict[str, Any], PaymentResolver.serialize_merchant(connection))

    @staticmethod
    async def get_connection(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        provider: str = "stub",
    ) -> MerchantConnection | None:
        return await PaymentResolver.resolve_merchant(
            session, business_id=business_id, provider=provider
        )

    @staticmethod
    async def upsert_connection(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        actor_id: uuid.UUID,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> MerchantConnection:
        business = await BusinessService.get_by_id(session, business_id)
        assert_business_mutable(business.state, action="update merchant connection")
        validated = validate_merchant_update_payload(payload)
        existing = await PaymentResolver.resolve_merchant(
            session, business_id=business_id, provider=validated["provider"]
        )
        before = MerchantService.serialize(existing) if existing else None
        if existing:
            existing.status = validated["status"]
            existing.provider_metadata = validated["provider_metadata"]
            existing.version += 1
            connection = existing
        else:
            connection = MerchantConnection(
                business_id=business_id,
                provider=validated["provider"],
                status=validated["status"],
                provider_metadata=validated["provider_metadata"],
            )
            session.add(connection)
        await session.flush()
        after = MerchantService.serialize(connection)
        await OutboxService.publish(
            session,
            event_type="payment.merchant.updated",
            payload={
                "business_id": str(business_id),
                "provider": connection.provider,
                "after": after,
            },
            business_id=business_id,
            correlation_id=correlation_id,
        )
        await AuditService.record(
            session,
            event_type="payment.merchant.updated",
            actor_identity_id=actor_id,
            actor_context="business",
            business_id=business_id,
            resource_type="merchant_connection",
            resource_id=connection.id,
            action="updated",
            before_state=before,
            after_state=after,
        )
        return connection
