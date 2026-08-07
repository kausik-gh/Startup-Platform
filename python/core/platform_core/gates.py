"""Canonical capability gates (Document 12 §8.9).

Each failed gate raises a distinct PlatformError code so Entitlement, module
state, Location, permission, and resource state remain independently enforceable.
"""

from __future__ import annotations

from collections.abc import Collection

from platform_core.exceptions import ResourceStateDenied

# Business lifecycle states that still permit ordinary mutations (Stage 1).
BUSINESS_MUTABLE_STATES: frozenset[str] = frozenset(
    {"draft", "onboarding", "active", "dormant"}
)

# Switching into a Business uses the same operable lifecycle set (not closed).
BUSINESS_SWITCHABLE_STATES: frozenset[str] = BUSINESS_MUTABLE_STATES


def assert_resource_allows(
    *,
    resource: str,
    current_state: str,
    allowed_states: Collection[str],
    action: str | None = None,
) -> None:
    """Gate [9]: resource/workflow state must permit the requested action."""
    allowed = frozenset(allowed_states)
    if current_state not in allowed:
        raise ResourceStateDenied(
            resource,
            current_state,
            action=action,
            allowed_states=sorted(allowed),
        )


def assert_business_mutable(state: str, *, action: str = "update") -> None:
    """Stage 1 resource gate over the Business lifecycle resource."""
    assert_resource_allows(
        resource="business",
        current_state=state,
        allowed_states=BUSINESS_MUTABLE_STATES,
        action=action,
    )


def assert_business_switchable(state: str) -> None:
    """Resource gate for entering/switching Business context."""
    assert_resource_allows(
        resource="business",
        current_state=state,
        allowed_states=BUSINESS_SWITCHABLE_STATES,
        action="switch",
    )
