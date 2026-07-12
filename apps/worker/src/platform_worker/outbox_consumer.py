from sqlalchemy.ext.asyncio import AsyncSession
from platform_worker.claiming import claim_outbox_batch


async def poll_and_dispatch_outbox(session: AsyncSession, worker_id: str) -> None:
    """
    Polls outbox events from platform_outbox_events and dispatches them to event handlers.
    """
    events = await claim_outbox_batch(session, worker_id)
    if not events:
        return

    print(f"[Outbox] Claimed {len(events)} events to process.")
    for event in events:
        # Under Stage 1A, we only log the claim. Handlers will be defined in later stages.
        print(f"[Outbox] Processing event: {event.get('id')} of type: {event.get('event_type')}")
        # In a full run: await dispatch_event_to_handlers(event, session)
