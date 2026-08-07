"""Super Admin APIs — includes Marketplace indexing health (Doc 11 §17.3)."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from platform_api.db import get_db_session
from platform_api.dependencies import require_super_admin
from platform_core.context import RequestContext
from platform_core.exceptions import ResourceNotFound
from platform_core.models import MarketplaceIndexHealth
from platform_core.services.audit import AuditService
from platform_core.services.business import BusinessService
from platform_core.services.marketplace_indexing import MarketplaceIndexingService

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/businesses/{business_id}")
async def admin_get_business(
    business_id: UUID,
    ctx: RequestContext = Depends(require_super_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    business = await BusinessService.get_by_id(session, business_id)
    if not business:
        raise ResourceNotFound("Business")

    await AuditService.record(
        session,
        event_type="admin.business.inspected",
        actor_identity_id=ctx.identity_id,
        actor_context="admin",
        business_id=business_id,
        resource_type="business",
        resource_id=business_id,
        action="inspect",
        after_state={"display_name": business.display_name, "state": business.state},
    )
    await session.commit()

    return {
        "data": {
            "id": str(business.id),
            "slug": business.slug,
            "display_name": business.display_name,
            "state": business.state,
            "visibility": business.visibility,
        },
        "meta": {"correlation_id": ctx.correlation_id},
    }


@router.get("/marketplace/indexing")
async def admin_list_indexing_health(
    status: str | None = Query(default=None),
    ctx: RequestContext = Depends(require_super_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    query = select(MarketplaceIndexHealth).order_by(
        MarketplaceIndexHealth.last_attempt_at.desc().nullslast()
    )
    if status:
        query = query.where(MarketplaceIndexHealth.last_status == status)
    rows = (await session.execute(query.limit(200))).scalars().all()

    dead_letters = await session.execute(
        text("""
            SELECT id, event_type, final_error, attempt_count, created_at
            FROM platform_dead_letter_events
            WHERE event_type LIKE 'marketplace.%'
               OR (payload::text LIKE '%marketplace%' AND source_table = 'platform_async_jobs')
            ORDER BY created_at DESC
            LIMIT 50
        """)
    )
    dl_rows = [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "final_error": r.final_error,
            "attempt_count": r.attempt_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in dead_letters
    ]
    return {
        "data": {
            "health": [MarketplaceIndexingService.serialize_health(h) for h in rows],
            "dead_letters": dl_rows,
        },
        "meta": {"correlation_id": ctx.correlation_id, "count": len(rows)},
    }


@router.get("/marketplace/indexing/{business_id}")
async def admin_get_indexing_health(
    business_id: UUID,
    ctx: RequestContext = Depends(require_super_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    business = await BusinessService.get_by_id(session, business_id)
    if not business:
        raise ResourceNotFound("Business")
    health = (
        await session.execute(
            select(MarketplaceIndexHealth).where(
                MarketplaceIndexHealth.business_id == business_id
            )
        )
    ).scalars().first()
    return {
        "data": {
            "business": {
                "id": str(business.id),
                "slug": business.slug,
                "visibility": business.visibility,
                "state": business.state,
            },
            "health": MarketplaceIndexingService.serialize_health(health) if health else None,
        },
        "meta": {"correlation_id": ctx.correlation_id},
    }


@router.post("/marketplace/indexing/{business_id}/reindex")
async def admin_reindex_business(
    business_id: UUID,
    ctx: RequestContext = Depends(require_super_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    business = await BusinessService.get_by_id(session, business_id)
    if not business:
        raise ResourceNotFound("Business")
    result = await MarketplaceIndexingService.reindex_business(
        session,
        business_id=business_id,
        correlation_id=ctx.correlation_id or str(uuid.uuid4()),
        actor_id=ctx.identity_id,
        trigger="admin_manual",
    )
    await AuditService.record(
        session,
        event_type="marketplace.reindex_triggered",
        actor_identity_id=ctx.identity_id,
        actor_context="admin",
        business_id=business_id,
        resource_type="marketplace_projection",
        resource_id=business_id,
        action="manual_reindex",
        after_state=result,
    )
    await session.commit()
    return {"data": result, "meta": {"correlation_id": ctx.correlation_id}}
