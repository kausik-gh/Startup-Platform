"""Booking availability and conflict prevention (Stage 7)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.exceptions import ConflictError, ValidationError
from platform_core.models import Booking, BusinessEmployeeLocationAssignment
from platform_core.resolvers.employee_resolver import EmployeeResolver
from platform_core.validation.booking import RESERVATION_MODES

ACTIVE_STATUSES = ("pending", "confirmed", "checked_in")


class AvailabilityService:
    @staticmethod
    async def _assert_employee_at_location(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        employee_id: uuid.UUID,
        location_id: uuid.UUID,
    ) -> None:
        await EmployeeResolver.resolve_operable(
            session, business_id=business_id, employee_id=employee_id
        )
        result = await session.execute(
            select(BusinessEmployeeLocationAssignment.id).where(
                BusinessEmployeeLocationAssignment.business_id == business_id,
                BusinessEmployeeLocationAssignment.employee_id == employee_id,
                BusinessEmployeeLocationAssignment.location_id == location_id,
            )
        )
        if result.scalars().first() is None:
            raise ValidationError(
                "Employee is not assigned to this location",
                details={"employee_id": str(employee_id), "location_id": str(location_id)},
            )

    @staticmethod
    async def _employee_conflict(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        employee_id: uuid.UUID,
        starts_at: Any,
        ends_at: Any,
        exclude_booking_id: uuid.UUID | None,
    ) -> bool:
        query = select(Booking.id).where(
            Booking.business_id == business_id,
            Booking.employee_id == employee_id,
            Booking.deleted_at.is_(None),
            Booking.status.in_(ACTIVE_STATUSES),
            Booking.starts_at < ends_at,
            Booking.ends_at > starts_at,
        )
        if exclude_booking_id:
            query = query.where(Booking.id != exclude_booking_id)
        return (await session.execute(query.limit(1))).scalars().first() is not None

    @staticmethod
    async def _capacity_usage(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        location_id: uuid.UUID,
        offering_id: uuid.UUID | None,
        reservation_mode: str,
        starts_at: Any,
        ends_at: Any,
        exclude_booking_id: uuid.UUID | None,
    ) -> int:
        query = select(func.coalesce(func.sum(Booking.party_size), 0)).where(
            Booking.business_id == business_id,
            Booking.location_id == location_id,
            Booking.reservation_mode == reservation_mode,
            Booking.deleted_at.is_(None),
            Booking.status.in_(ACTIVE_STATUSES),
            Booking.starts_at < ends_at,
            Booking.ends_at > starts_at,
        )
        if offering_id:
            query = query.where(Booking.offering_id == offering_id)
        if exclude_booking_id:
            query = query.where(Booking.id != exclude_booking_id)
        result = await session.execute(query)
        return int(result.scalar_one())

    @staticmethod
    async def assert_available(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        location_id: uuid.UUID,
        employee_id: uuid.UUID | None,
        offering_id: uuid.UUID | None,
        reservation_mode: str,
        starts_at: Any,
        ends_at: Any,
        party_size: int,
        capacity: int | None,
        exclude_booking_id: uuid.UUID | None = None,
    ) -> None:
        if reservation_mode not in RESERVATION_MODES:
            raise ValidationError("Invalid reservation mode")

        if employee_id:
            await AvailabilityService._assert_employee_at_location(
                session,
                business_id=business_id,
                employee_id=employee_id,
                location_id=location_id,
            )
            if await AvailabilityService._employee_conflict(
                session,
                business_id=business_id,
                employee_id=employee_id,
                starts_at=starts_at,
                ends_at=ends_at,
                exclude_booking_id=exclude_booking_id,
            ):
                raise ConflictError(
                    "Employee is not available for this time slot",
                    details={"employee_id": str(employee_id)},
                )

        if reservation_mode in {"table", "class_session", "rental", "accommodation"} and capacity:
            used = await AvailabilityService._capacity_usage(
                session,
                business_id=business_id,
                location_id=location_id,
                offering_id=offering_id,
                reservation_mode=reservation_mode,
                starts_at=starts_at,
                ends_at=ends_at,
                exclude_booking_id=exclude_booking_id,
            )
            if used + party_size > capacity:
                raise ConflictError(
                    "Capacity exceeded for this time slot",
                    details={
                        "capacity": capacity,
                        "used": used,
                        "requested": party_size,
                    },
                )

    @staticmethod
    async def check_availability(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            await AvailabilityService.assert_available(
                session,
                business_id=business_id,
                location_id=params["location_id"],
                employee_id=params.get("employee_id"),
                offering_id=params.get("offering_id"),
                reservation_mode=params["reservation_mode"],
                starts_at=params["starts_at"],
                ends_at=params["ends_at"],
                party_size=params["party_size"],
                capacity=params.get("capacity"),
                exclude_booking_id=params.get("exclude_booking_id"),
            )
            available = True
            reason = None
        except ConflictError as exc:
            available = False
            reason = str(getattr(exc, "detail", exc))
            if isinstance(exc.detail, dict):
                reason = str(exc.detail.get("message", reason))
        return {"available": available, "reason": reason}
