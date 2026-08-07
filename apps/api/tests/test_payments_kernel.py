"""Stage 9 — Payments Kernel tests."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import jwt
import pytest
from fastapi.testclient import TestClient
from platform_api.main import app
from platform_core.db import get_database_url
from platform_core.models import PlatformAuditEvent, PlatformOutboxEvent
from platform_testing.db_helpers import ensure_auth_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"
WEBHOOK_SECRET = "test-payment-webhook-secret"


def _token(sub: uuid.UUID, email: str) -> str:
    return jwt.encode(
        {
            "sub": str(sub),
            "email": email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


def _headers(user_id: uuid.UUID, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user_id, email)}"}


def _seed(user_id: uuid.UUID, email: str) -> None:
    async def _run() -> None:
        url = get_database_url()
        assert url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            await ensure_auth_user(session, user_id, email)
            await session.commit()
        await engine.dispose()

    asyncio.run(_run())


@pytest.fixture
def owner(monkeypatch: Any) -> tuple[dict[str, str], uuid.UUID]:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET", WEBHOOK_SECRET)
    user_id = uuid.uuid4()
    email = f"{user_id}@example.com"
    _seed(user_id, email)
    return _headers(user_id, email), user_id


def _create_business(client: TestClient, headers: dict[str, str]) -> str:
    resp = client.post(
        "/v1/platform/businesses",
        json={"display_name": f"Payments Co {uuid.uuid4().hex[:8]}", "business_type": "retail"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return cast(str, resp.json()["data"]["business"]["id"])


def _primary_location_id(client: TestClient, headers: dict[str, str], business_id: str) -> str:
    resp = client.get(f"/v1/platform/businesses/{business_id}/locations", headers=headers)
    assert resp.status_code == 200, resp.text
    for loc in resp.json()["data"]:
        if loc["is_primary"]:
            return cast(str, loc["id"])
    raise AssertionError("primary location missing")


def _create_customer(client: TestClient, headers: dict[str, str], business_id: str) -> str:
    resp = client.post(
        f"/v1/platform/businesses/{business_id}/customers",
        json={"display_name": "Payment Buyer", "email": f"{uuid.uuid4()}@example.com"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return cast(str, resp.json()["data"]["id"])


def _create_tracked_product(client: TestClient, headers: dict[str, str], business_id: str) -> str:
    product_id = client.post(
        f"/v1/platform/businesses/{business_id}/products",
        json={
            "title": f"Pay Widget {uuid.uuid4().hex[:6]}",
            "sku": f"PAY-{uuid.uuid4().hex[:8]}",
            "track_inventory": True,
            "status": "active",
            "price_amount": 100.0,
            "tax_rate": 10.0,
        },
        headers=headers,
    ).json()["data"]["id"]
    return cast(str, product_id)


def _stock_product(
    client: TestClient,
    headers: dict[str, str],
    business_id: str,
    product_id: str,
    location_id: str,
    quantity: int = 50,
) -> None:
    resp = client.post(
        f"/v1/platform/businesses/{business_id}/inventory/opening-stock",
        json={
            "offering_id": product_id,
            "location_id": location_id,
            "quantity": quantity,
            "reason": "Test stock",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _create_order(
    client: TestClient,
    headers: dict[str, str],
    business_id: str,
    location_id: str,
    product_id: str,
    customer_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "location_id": location_id,
        "payment_method": "cod",
        "items": [{"offering_id": product_id, "quantity": 2}],
    }
    if customer_id:
        payload["customer_contact_id"] = customer_id
    resp = client.post(
        f"/v1/platform/businesses/{business_id}/orders",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return cast(dict[str, Any], resp.json()["data"])


def _webhook_signature(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_cod_payment_offline_settlement_and_order_sync(owner: tuple[dict[str, str], uuid.UUID]) -> None:
    headers, _ = owner
    client = TestClient(app)
    business_id = _create_business(client, headers)
    location_id = _primary_location_id(client, headers, business_id)
    customer_id = _create_customer(client, headers, business_id)
    product_id = _create_tracked_product(client, headers, business_id)
    _stock_product(client, headers, business_id, product_id, location_id)
    order = _create_order(client, headers, business_id, location_id, product_id, customer_id)
    order_total = order["total_amount"]

    idempotency_key = str(uuid.uuid4())
    pay_resp = client.post(
        f"/v1/platform/businesses/{business_id}/payments",
        json={
            "source_type": "order",
            "source_id": order["id"],
            "amount": order_total,
            "payment_method": "cod",
            "idempotency_key": idempotency_key,
        },
        headers=headers,
    )
    assert pay_resp.status_code == 200, pay_resp.text
    payment = pay_resp.json()["data"]
    assert payment["status"] == "pending_offline"
    payment_id = payment["id"]

    dup_resp = client.post(
        f"/v1/platform/businesses/{business_id}/payments",
        json={
            "source_type": "order",
            "source_id": order["id"],
            "amount": order_total,
            "payment_method": "cod",
            "idempotency_key": idempotency_key,
        },
        headers=headers,
    )
    assert dup_resp.status_code == 200, dup_resp.text
    assert dup_resp.json()["data"]["id"] == payment_id

    order_resp = client.get(
        f"/v1/platform/businesses/{business_id}/orders/{order['id']}",
        headers=headers,
    )
    assert order_resp.json()["data"]["payment_status"] == "pending_offline"

    settle_resp = client.post(
        f"/v1/platform/businesses/{business_id}/payments/{payment_id}/record-settlement",
        json={"version": payment["version"]},
        headers=headers,
    )
    assert settle_resp.status_code == 200, settle_resp.text
    assert settle_resp.json()["data"]["status"] == "succeeded"

    order_resp = client.get(
        f"/v1/platform/businesses/{business_id}/orders/{order['id']}",
        headers=headers,
    )
    assert order_resp.json()["data"]["payment_status"] == "paid"


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_online_payment_webhook_and_refund(owner: tuple[dict[str, str], uuid.UUID]) -> None:
    headers, _ = owner
    client = TestClient(app)
    business_id = _create_business(client, headers)
    location_id = _primary_location_id(client, headers, business_id)
    product_id = _create_tracked_product(client, headers, business_id)
    _stock_product(client, headers, business_id, product_id, location_id)
    order = _create_order(client, headers, business_id, location_id, product_id)

    pay_resp = client.post(
        f"/v1/platform/businesses/{business_id}/payments",
        json={
            "source_type": "order",
            "source_id": order["id"],
            "amount": order["total_amount"],
            "payment_method": "online",
        },
        headers=headers,
    )
    assert pay_resp.status_code == 200, pay_resp.text
    payment = pay_resp.json()["data"]
    assert payment["status"] == "processing"
    payment_id = payment["id"]

    payload = {
        "event_id": str(uuid.uuid4()),
        "payment_id": payment_id,
        "status": "succeeded",
        "provider_reference": "stub-ref-001",
    }
    raw = json.dumps(payload).encode()
    sig = _webhook_signature(raw)
    webhook_resp = client.post(
        "/v1/webhooks/payments/stub",
        content=raw,
        headers={"Content-Type": "application/json", "x-payment-signature": sig},
    )
    assert webhook_resp.status_code == 200, webhook_resp.text
    assert webhook_resp.json()["data"]["status"] == "processed"

    get_resp = client.get(
        f"/v1/platform/businesses/{business_id}/payments/{payment_id}",
        headers=headers,
    )
    assert get_resp.json()["data"]["status"] == "succeeded"

    refund_resp = client.post(
        f"/v1/platform/businesses/{business_id}/payments/{payment_id}/refunds",
        json={"amount": order["total_amount"], "reason": "Customer return", "version": get_resp.json()["data"]["version"]},
        headers=headers,
    )
    assert refund_resp.status_code == 200, refund_resp.text
    assert refund_resp.json()["data"]["payment"]["status"] == "refunded"


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_payment_webhook_rejects_invalid_signature(owner: tuple[dict[str, str], uuid.UUID]) -> None:
    headers, _ = owner
    client = TestClient(app)
    payload = {"event_id": str(uuid.uuid4()), "payment_id": str(uuid.uuid4()), "status": "succeeded"}
    raw = json.dumps(payload).encode()
    resp = client.post(
        "/v1/webhooks/payments/stub",
        content=raw,
        headers={"Content-Type": "application/json", "x-payment-signature": "bad-signature"},
    )
    assert resp.status_code == 422 or resp.status_code == 400


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_payment_business_isolation(owner: tuple[dict[str, str], uuid.UUID]) -> None:
    headers_a, _ = owner
    client = TestClient(app)
    business_a = _create_business(client, headers_a)
    location_a = _primary_location_id(client, headers_a, business_a)
    product_a = _create_tracked_product(client, headers_a, business_a)
    _stock_product(client, headers_a, business_a, product_a, location_a)
    order_a = _create_order(client, headers_a, business_a, location_a, product_a)

    user_b = uuid.uuid4()
    email_b = f"{user_b}@example.com"
    _seed(user_b, email_b)
    headers_b = _headers(user_b, email_b)
    business_b = _create_business(client, headers_b)

    pay_a = client.post(
        f"/v1/platform/businesses/{business_a}/payments",
        json={
            "source_type": "order",
            "source_id": order_a["id"],
            "amount": order_a["total_amount"],
            "payment_method": "cod",
        },
        headers=headers_a,
    ).json()["data"]

    denied = client.get(
        f"/v1/platform/businesses/{business_b}/payments/{pay_a['id']}",
        headers=headers_b,
    )
    assert denied.status_code == 403 or denied.status_code == 404


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_payment_audit_and_outbox(owner: tuple[dict[str, str], uuid.UUID]) -> None:
    headers, _ = owner
    client = TestClient(app)
    business_id = _create_business(client, headers)
    location_id = _primary_location_id(client, headers, business_id)
    product_id = _create_tracked_product(client, headers, business_id)
    _stock_product(client, headers, business_id, product_id, location_id)
    order = _create_order(client, headers, business_id, location_id, product_id)

    pay_resp = client.post(
        f"/v1/platform/businesses/{business_id}/payments",
        json={
            "source_type": "order",
            "source_id": order["id"],
            "amount": order["total_amount"],
            "payment_method": "cod",
        },
        headers=headers,
    )
    payment_id = pay_resp.json()["data"]["id"]

    async def _check() -> None:
        url = get_database_url()
        assert url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            outbox = await session.execute(
                select(PlatformOutboxEvent).where(
                    PlatformOutboxEvent.business_id == uuid.UUID(business_id),
                    PlatformOutboxEvent.event_type == "payment.initiated",
                )
            )
            assert outbox.scalars().first() is not None
            audit = await session.execute(
                select(PlatformAuditEvent).where(
                    PlatformAuditEvent.business_id == uuid.UUID(business_id),
                    PlatformAuditEvent.resource_id == uuid.UUID(payment_id),
                )
            )
            assert audit.scalars().first() is not None
        await engine.dispose()

    asyncio.run(_check())


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL required")
def test_merchant_connection_upsert(owner: tuple[dict[str, str], uuid.UUID]) -> None:
    headers, _ = owner
    client = TestClient(app)
    business_id = _create_business(client, headers)

    resp = client.put(
        f"/v1/platform/businesses/{business_id}/payments/merchant-connection",
        json={"provider": "stub", "status": "active", "provider_metadata": {"merchant_ref": "m-1"}},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "active"

    get_resp = client.get(
        f"/v1/platform/businesses/{business_id}/payments/merchant-connection?provider=stub",
        headers=headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["data"]["provider_metadata"]["merchant_ref"] == "m-1"
