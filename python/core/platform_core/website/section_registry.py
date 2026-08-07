"""Platform-defined website section types (Doc 12 §11.1)."""

from __future__ import annotations

from typing import Any

# Minimal in-process schemas used when DB seed is unavailable (tests / bootstrap).
CORE_SECTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "hero": {
        "type": "object",
        "required": ["headline"],
        "properties": {
            "headline": {"type": "string", "maxLength": 120},
            "subheadline": {"type": "string", "maxLength": 300},
            "cta_label": {"type": "string", "maxLength": 60},
            "cta_url": {"type": "string", "maxLength": 200},
            "image_asset_id": {"type": "string", "format": "uuid"},
        },
    },
    "about": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 120},
            "body": {"type": "string", "maxLength": 2000},
            "image_asset_id": {"type": "string", "format": "uuid"},
        },
    },
    "contact": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 120},
            "address": {"type": "string", "maxLength": 500},
            "phone": {"type": "string", "maxLength": 50},
            "email": {"type": "string", "maxLength": 200},
            "hours_summary": {"type": "string", "maxLength": 500},
            "show_map": {"type": "boolean"},
        },
    },
    "text_block": {
        "type": "object",
        "required": ["body"],
        "properties": {
            "title": {"type": "string", "maxLength": 120},
            "body": {"type": "string", "maxLength": 5000},
        },
    },
    "location_list": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 120},
            "show_hours": {"type": "boolean"},
            "show_map": {"type": "boolean"},
        },
    },
    "offerings_list": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 120},
            "subtitle": {"type": "string", "maxLength": 300},
            "offering_types": {"type": "array", "items": {"type": "string"}},
            "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
        },
    },
    "cta_band": {
        "type": "object",
        "required": ["headline", "cta_label"],
        "properties": {
            "headline": {"type": "string", "maxLength": 200},
            "body": {"type": "string", "maxLength": 500},
            "cta_label": {"type": "string", "maxLength": 60},
            "cta_url": {"type": "string", "maxLength": 200},
        },
    },
}

ALLOWED_SECTION_TYPE_IDS = frozenset(CORE_SECTION_SCHEMAS.keys())

WEBSITE_GENERATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["pages", "navigation", "theme_hints"],
    "properties": {
        "pages": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["slug", "title", "page_type", "sections"],
                "properties": {
                    "slug": {"type": "string"},
                    "title": {"type": "string"},
                    "page_type": {"type": "string"},
                    "seo_title": {"type": "string"},
                    "seo_description": {"type": "string"},
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["section_type_id", "content"],
                            "properties": {
                                "section_type_id": {"type": "string"},
                                "layout_variant": {"type": "string"},
                                "content": {"type": "object"},
                                "module_binding": {"type": "object"},
                                "is_visible": {"type": "boolean"},
                            },
                        },
                    },
                },
            },
        },
        "navigation": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label", "path"],
                "properties": {
                    "label": {"type": "string"},
                    "path": {"type": "string"},
                },
            },
        },
        "theme_hints": {"type": "object"},
    },
}

# Doc 12 §11.4 typical page sets by business type
PAGES_BY_BUSINESS_TYPE: dict[str, list[tuple[str, str, str]]] = {
    "restaurant": [
        ("home", "Home", "home"),
        ("menu", "Menu", "menu"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "cafe": [
        ("home", "Home", "home"),
        ("menu", "Menu", "menu"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "retail": [
        ("home", "Home", "home"),
        ("products", "Products", "offerings"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "salon": [
        ("home", "Home", "home"),
        ("services", "Services", "services"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "spa": [
        ("home", "Home", "home"),
        ("services", "Services", "services"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "hotel": [
        ("home", "Home", "home"),
        ("rooms", "Rooms", "rooms"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "homestay": [
        ("home", "Home", "home"),
        ("rooms", "Rooms", "rooms"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "gym": [
        ("home", "Home", "home"),
        ("plans", "Plans", "plans"),
        ("classes", "Classes", "classes"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "studio": [
        ("home", "Home", "home"),
        ("classes", "Classes", "classes"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
    "professional_service": [
        ("home", "Home", "home"),
        ("services", "Services", "services"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
        ("enquire", "Enquire", "enquire"),
    ],
    "education": [
        ("home", "Home", "home"),
        ("courses", "Courses", "offerings"),
        ("about", "About", "about"),
        ("contact", "Contact", "contact"),
    ],
}

DEFAULT_PAGES: list[tuple[str, str, str]] = [
    ("home", "Home", "home"),
    ("about", "About", "about"),
    ("contact", "Contact", "contact"),
]
