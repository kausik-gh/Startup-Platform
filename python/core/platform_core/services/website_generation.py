"""Website AI generation orchestration (Doc 12 §12.1–§12.2)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.exceptions import ConflictError, ValidationError
from platform_core.gates import assert_business_mutable
from platform_core.models import BusinessProfile, WebsiteGenerationJob
from platform_core.resolvers.website_resolver import WebsiteResolver
from platform_core.services.async_jobs import AsyncJobService
from platform_core.services.audit import AuditService
from platform_core.services.business import BusinessService
from platform_core.services.outbox import OutboxService
from platform_core.services.website import WebsiteService
from platform_core.validation.website import validate_generation_payload
from platform_core.website.ai_provider import get_ai_provider
from platform_core.website.fallback_generator import build_deterministic_draft
from platform_core.website.section_registry import WEBSITE_GENERATION_SCHEMA


class WebsiteGenerationService:
    @staticmethod
    async def enqueue_generation(
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        actor_id: uuid.UUID,
        correlation_id: str,
        auto: bool = False,
    ) -> WebsiteGenerationJob:
        business = await BusinessService.get_by_id(session, business_id)
        assert_business_mutable(business.state, action="generate website")
        await WebsiteService.provision_for_business(
            session, business_id=business_id, actor_id=actor_id
        )

        running = await session.execute(
            select(WebsiteGenerationJob).where(
                WebsiteGenerationJob.business_id == business_id,
                WebsiteGenerationJob.status.in_(("pending", "running")),
            )
        )
        existing = running.scalars().first()
        if existing is not None:
            raise ConflictError(
                "Website generation already in progress",
                details={"job_id": str(existing.id), "status": existing.status},
            )

        job = WebsiteGenerationJob(
            business_id=business_id,
            status="pending",
            prompt_version="v1",
            triggered_by=actor_id,
        )
        session.add(job)
        await session.flush()

        await AsyncJobService.enqueue(
            session,
            job_type="website.generate",
            payload={
                "business_id": str(business_id),
                "generation_job_id": str(job.id),
                "triggered_by": str(actor_id),
                "correlation_id": correlation_id,
                "auto": auto,
            },
            business_id=business_id,
            max_attempts=3,
        )
        return job

    @staticmethod
    async def _load_context(
        session: AsyncSession, business_id: uuid.UUID
    ) -> dict[str, Any]:
        business = await BusinessService.get_by_id(session, business_id)
        profile_result = await session.execute(
            select(BusinessProfile).where(BusinessProfile.business_id == business_id)
        )
        profile = profile_result.scalars().first()
        return {
            "display_name": business.display_name,
            "business_type": business.business_type,
            "tagline": profile.tagline if profile else None,
            "description": profile.description if profile else None,
        }

    @staticmethod
    async def _try_ai(context: dict[str, Any]) -> dict[str, Any]:
        from platform_core.website.ai_provider import UnavailableAIProvider

        provider = get_ai_provider()
        # Unconfigured provider (FL-DEC-015) fails immediately — no retry delay.
        if isinstance(provider, UnavailableAIProvider):
            raise RuntimeError(
                "AI provider not configured (FL-DEC-015 unresolved); use deterministic fallback"
            )
        prompt = (
            f"Generate a structured multi-page business website draft for "
            f"{context['display_name']} ({context.get('business_type') or 'business'})."
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                raw = await provider.generate_structured(
                    prompt,
                    WEBSITE_GENERATION_SCHEMA,
                    {"purpose": "website.generate"},
                    timeout_seconds=30,
                )
                return validate_generation_payload(raw)
            except Exception as exc:  # noqa: BLE001 — retry then fallback
                last_error = exc
                await asyncio.sleep(min(2**attempt, 8))
        raise RuntimeError(str(last_error or "AI generation failed"))

    @staticmethod
    async def execute_job(
        session: AsyncSession,
        *,
        generation_job_id: uuid.UUID,
        correlation_id: str,
    ) -> dict[str, Any]:
        result = await session.execute(
            select(WebsiteGenerationJob).where(WebsiteGenerationJob.id == generation_job_id)
        )
        job = result.scalars().first()
        if job is None:
            raise ValidationError("Generation job not found")
        if job.status in {"completed", "fallback_used"}:
            return {"status": job.status, "job_id": str(job.id), "duplicate": True}

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.attempt_count = (job.attempt_count or 0) + 1
        await session.flush()

        website = await WebsiteResolver.resolve_website(session, business_id=job.business_id)
        context = await WebsiteGenerationService._load_context(session, job.business_id)
        generated_by = "ai_generation"
        fallback_reason: str | None = None
        try:
            payload = await WebsiteGenerationService._try_ai(context)
            job.ai_provider = "configured"
            job.model_name = "structured"
        except Exception as exc:  # noqa: BLE001
            payload = build_deterministic_draft(
                display_name=context["display_name"],
                business_type=context.get("business_type"),
                tagline=context.get("tagline"),
                description=context.get("description"),
            )
            payload = validate_generation_payload(payload)
            generated_by = "deterministic_fallback"
            fallback_reason = str(exc)
            job.fallback_reason = fallback_reason
            job.ai_provider = None
            job.model_name = None

        draft = await WebsiteService.replace_draft_from_generation(
            session,
            business_id=job.business_id,
            website=website,
            payload=payload,
            generated_by=generated_by,
            generation_job_id=job.id,
        )
        job.result_version_id = draft.id
        job.completed_at = datetime.now(timezone.utc)
        job.status = "fallback_used" if generated_by == "deterministic_fallback" else "completed"
        await session.flush()

        await OutboxService.publish(
            session,
            event_type="website.draft_generated",
            payload={
                "business_id": str(job.business_id),
                "website_id": str(website.id),
                "version_id": str(draft.id),
                "generated_by": generated_by,
                "generation_job_id": str(job.id),
            },
            business_id=job.business_id,
            correlation_id=correlation_id,
        )
        await AuditService.record(
            session,
            event_type="website.draft_generated",
            actor_identity_id=job.triggered_by,
            actor_context="business",
            business_id=job.business_id,
            resource_type="website_version",
            resource_id=draft.id,
            action="generated",
            after_state={
                "generated_by": generated_by,
                "fallback_reason": fallback_reason,
                "job_status": job.status,
            },
        )
        if generated_by == "deterministic_fallback":
            await OutboxService.publish(
                session,
                event_type="website.generation_failed",
                payload={
                    "business_id": str(job.business_id),
                    "generation_job_id": str(job.id),
                    "fallback_reason": fallback_reason,
                },
                business_id=job.business_id,
                correlation_id=correlation_id,
            )
            await AuditService.record(
                session,
                event_type="website.generation_failed",
                actor_identity_id=job.triggered_by,
                actor_context="business",
                business_id=job.business_id,
                resource_type="website_generation_job",
                resource_id=job.id,
                action="fell_back",
                after_state={"fallback_reason": fallback_reason},
            )
        return {
            "status": job.status,
            "job_id": str(job.id),
            "version_id": str(draft.id),
            "generated_by": generated_by,
        }

    @staticmethod
    def serialize_job(job: WebsiteGenerationJob) -> dict[str, Any]:
        return {
            "id": str(job.id),
            "business_id": str(job.business_id),
            "status": job.status,
            "ai_provider": job.ai_provider,
            "model_name": job.model_name,
            "prompt_version": job.prompt_version,
            "attempt_count": job.attempt_count,
            "error_detail": job.error_detail,
            "fallback_reason": job.fallback_reason,
            "result_version_id": str(job.result_version_id) if job.result_version_id else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
