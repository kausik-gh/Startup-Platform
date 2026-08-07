"""Booking domain service (Stage 7)."""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.exceptions import ConflictError, ValidationError
from platform_core.gates import assert_business_mutable
from platform_core.models import Booking, BookingStatusHistory
from platform_core.resolvers.customer_resolver import CustomerResolver
from platform_core.resolvers.location_resolver import LocationResolver
from platform_core.resolvers.offering_resolver import OfferingResolver
from platform_core.resolvers.booking_resolver import BookingResolver
from platform_core.services.audit import AuditService
from platform_core.services.availability import AvailabilityService
from platform_core.services.business import BusinessService
from platform_core.services.customer_timeline import CustomerTimelineService
from platform_core.services.outbox import OutboxService
from platform_core.validation.booking import (
    RESERVABLE_OFFERING_TYPES,
    validate_create_payload,
    validate_patch_payload,
)


class BookingService:
    @staticmethod
    def serialize(booking: Booking) -> dict[str, Any]:
        return cast(dict[str, Any], BookingResolver.serialize_booking(booking))

    @staticmethod
    def _generate_booking_number() -> str:
        return f"BKG-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    async def list_for_business(
        session: AsyncSession,
        business_id: uuid.UUID,
        *,
        status: str | None = None,
        search: str | None = None,
        customer_contact_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        employee_id: uuid.UUID | None = None,
    ) -> list[Booking]:
        query = select(Booking).where(
            Booking.business_id == business_id,
            Booking.deleted_at.is_(None),
        )
        if status:
            query = query.where(Booking.status == status)
        if customer_contact_id:
            query = query.where(Booking.customer_contact_id == customer_contact_id)
        if location_id:
            query = query.where(Booking.location_id == location_id)
        if employee_id:
            query = query.where(Booking.employee_id == employee_id)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Booking.booking_number.ilike(pattern),
                    Booking.title.ilike(pattern),
                    Booking.internal_reference.ilike(pattern),
                )
            )
        query = query.order_by(Booking.starts_at.desc())
        return list((await session.execute(query)).scalars().all())

    @staticmethod
    async def create_booking(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        actor_id: uuid.UUID,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> Booking:
        business = await BusinessService.get_by_id(session, business_id)
        assert_business_mutable(business.status, action="create booking")
        validated = validate_create_payload(payload)

        if validated["idempotency_key"]:
            existing = await session.execute(
                select(Booking).where(
                    Booking.business_id == business_id,
                    Booking.idempotency_key == validated["idempotency_key"],
                    Booking.deleted_at.is_(None),
                )
            )
            found = existing.scalars().first()
            if found:
                return found

        await LocationResolver.resolve(
            session, business_id=business_id, location_id=validated["location_id"]
        )
        if validated["customer_contact_id"]:
            await CustomerResolver.resolve(
                session,
                business_id=business_id,
                contact_id=validated["customer_contact_id"],
            )

        title = validated["title"]
        capacity = validated["capacity"]
        if validated["offering_id"]:
            offering = await OfferingResolver.resolve(
                session,
                business_id=business_id,
                offering_id=validated["offering_id"],
            )
            if offering.status != "active":
                raise ValidationError(
                    "Offering is not active",
                    details={"offering_id": str(offering.id)},
                )
            if offering.offering_type not in RESERVABLE_OFFERING_TYPES:
                raise ValidationError(
                    "Offering type is not reservable",
                    details={"offering_type": offering.offering_type},
                )
            title = title or offering.title

        if not title:
            raise ValidationError(
                "Booking title is required",
                details={"field": "title"},
            )

        await AvailabilityService.assert_available(
            session,
            business_id=business_id,
            location_id=validated["location_id"],
            employee_id=validated["employee_id"],
            offering_id=validated["offering_id"],
            reservation_mode=validated["reservation_mode"],
            starts_at=validated["starts_at"],
            ends_at=validated["ends_at"],
            party_size=validated["party_size"],
            capacity=capacity,
        )

        booking = Booking(
            business_id=business_id,
            location_id=validated["location_id"],
            customer_contact_id=validated["customer_contact_id"],
            offering_id=validated["offering_id"],
            employee_id=validated["employee_id"],
            booking_number=BookingService._generate_booking_number(),
            reservation_mode=validated["reservation_mode"],
            title=title,
            starts_at=validated["starts_at"],
            ends_at=validated["ends_at"],
            party_size=validated["party_size"],
            guest_count=validated["guest_count"],
            capacity=capacity,
            payment_method=validated["payment_method"],
            payment_status=(
                "pending_offline"
                if validated["payment_method"] in {"cod", "pay_at_business", "pay_later"}
                else "pending"
            ),
            internal_reference=validated["internal_reference"],
            idempotency_key=validated["idempotency_key"],
        )
        session.add(booking)
        await session.flush()

        history = BookingStatusHistory(
            business_id=business_id,
            booking_id=booking.id,
            from_status=None,
            to_status="pending",
            actor_identity_id=actor_id,
            reason="Booking created",
        )
        session.add(history)
        await session.flush()

        after = BookingResolver.serialize_booking(booking)
        await OutboxService.publish(
            session,
            event_type="booking.created",
            payload={
                "business_id": str(business_id),
                "booking_id": str(booking.id),
                "booking_number": booking.booking_number,
                "customer_contact_id": (
                    str(booking.customer_contact_id) if booking.customer_contact_id else None
                ),
                "starts_at": booking.starts_at.isoformat(),
                "ends_at": booking.ends_at.isoformat(),
                "after": after,
            },
            business_id=business_id,
            correlation_id=correlation_id,
        )
        await AuditService.record(
            session,
            event_type="booking.created",
            actor_identity_id=actor_id,
            actor_context="business",
            business_id=business_id,
            resource_type="booking",
            resource_id=booking.id,
            action="created",
            before_state=None,
            after_state=after,
        )
        if booking.customer_contact_id:
            await CustomerTimelineService.record_entry(
                session,
                business_id=business_id,
                contact_id=booking.customer_contact_id,
                activity_type="booking.created",
                resource_type="booking",
                resource_id=booking.id,
                location_id=booking.location_id,
                summary={
                    "booking_number": booking.booking_number,
                    "starts_at": booking.starts_at.isoformat(),
                    "status": booking.status,
                },
            )
        return booking

    @staticmethod
    async def patch_booking(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        booking_id: uuid.UUID,
        actor_id: uuid.UUID,
        correlation_id: str,
        payload: dict[str, Any],
        expected_version: int | None = None,
    ) -> Booking:
        business = await BusinessService.get_by_id(session, business_id)
        assert_business_mutable(business.status, action="update booking")
        booking = await BookingResolver.resolve_mutable(
            session, business_id=business_id, booking_id=booking_id
        )
        if expected_version is not None and booking.version != expected_version:
            raise ConflictError(
                "Stale booking version",
                details={
                    "expected_version": expected_version,
                    "current_version": booking.version,
                },
            )
        before = BookingResolver.serialize_booking(booking)
        patch = validate_patch_payload(payload)
        for key, value in patch.items():
            setattr(booking, key, value)
        booking.version += 1
        await session.flush()
        after = BookingResolver.serialize_booking(booking)
        await OutboxService.publish(
            session,
            event_type="booking.updated",
            payload={
                "business_id": str(business_id),
                "booking_id": str(booking.id),
                "after": after,
            },
            business_id=business_id,
            correlation_id=correlation_id,
        )
        await AuditService.record(
            session,
            event_type="booking.updated",
            actor_identity_id=actor_id,
            actor_context="business",
            business_id=business_id,
            resource_type="booking",
            resource_id=booking.id,
            action="updated",
            before_state=before,
            after_state=after,
        )
        return booking

    @staticmethod
    async def get_status_history(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        booking_id: uuid.UUID,
    ) -> list[BookingStatusHistory]:
        await BookingResolver.resolve(session, business_id=business_id, booking_id=booking_id)
        return await BookingResolver.load_status_history(session, booking_id=booking_id)
