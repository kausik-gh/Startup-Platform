"""Deterministic website draft generator (Doc 12 §12.1 — mandatory fallback)."""

from __future__ import annotations

from typing import Any

from platform_core.website.section_registry import DEFAULT_PAGES, PAGES_BY_BUSINESS_TYPE


def build_deterministic_draft(
    *,
    display_name: str,
    business_type: str | None,
    tagline: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Always returns a valid WebsiteGenerationSchema payload."""
    name = (display_name or "Your Business").strip() or "Your Business"
    btype = (business_type or "other").strip().lower()
    pages_spec = PAGES_BY_BUSINESS_TYPE.get(btype, DEFAULT_PAGES)
    tagline_text = (tagline or f"Welcome to {name}").strip()
    about_body = (description or f"{name} is ready to serve you. Update this page with your story.").strip()

    pages: list[dict[str, Any]] = []
    navigation: list[dict[str, str]] = []

    for sort_idx, (slug, title, page_type) in enumerate(pages_spec):
        navigation.append({"label": title, "path": f"/{slug}" if slug != "home" else "/"})
        sections: list[dict[str, Any]] = []
        if page_type == "home":
            sections = [
                {
                    "section_type_id": "hero",
                    "layout_variant": "centered",
                    "content": {
                        "headline": name,
                        "subheadline": tagline_text,
                        "cta_label": "Contact us",
                        "cta_url": "/contact",
                    },
                    "is_visible": True,
                },
                {
                    "section_type_id": "cta_band",
                    "layout_variant": "centered",
                    "content": {
                        "headline": f"Discover {name}",
                        "body": "Browse what we offer and get in touch.",
                        "cta_label": "About us",
                        "cta_url": "/about",
                    },
                    "is_visible": True,
                },
            ]
        elif page_type in {"about"}:
            sections = [
                {
                    "section_type_id": "about",
                    "layout_variant": "text_only",
                    "content": {"title": f"About {name}", "body": about_body},
                    "is_visible": True,
                }
            ]
        elif page_type == "contact":
            sections = [
                {
                    "section_type_id": "contact",
                    "layout_variant": "full",
                    "content": {
                        "title": "Contact",
                        "address": "Add your address",
                        "phone": "",
                        "email": "",
                        "hours_summary": "Update your opening hours",
                        "show_map": False,
                    },
                    "is_visible": True,
                }
            ]
        elif page_type in {"offerings", "services", "menu", "rooms", "plans", "classes"}:
            sections = [
                {
                    "section_type_id": "offerings_list",
                    "layout_variant": "cards",
                    "content": {
                        "title": title,
                        "subtitle": f"Explore {title.lower()} from {name}",
                        "max_items": 12,
                    },
                    "module_binding": {"module": "offerings-catalog"},
                    "is_visible": True,
                }
            ]
        elif page_type == "enquire":
            sections = [
                {
                    "section_type_id": "text_block",
                    "layout_variant": "default",
                    "content": {
                        "title": "Enquire",
                        "body": "Tell us what you need and we will get back to you.",
                    },
                    "is_visible": True,
                }
            ]
        else:
            sections = [
                {
                    "section_type_id": "text_block",
                    "layout_variant": "default",
                    "content": {"title": title, "body": f"Content for {title}."},
                    "is_visible": True,
                }
            ]

        pages.append(
            {
                "slug": slug,
                "title": title,
                "page_type": page_type,
                "seo_title": f"{title} | {name}",
                "seo_description": tagline_text[:160],
                "sort_order": sort_idx,
                "sections": sections,
            }
        )

    return {
        "pages": pages,
        "navigation": navigation,
        "theme_hints": {
            "primary_color": "#0F766E",
            "accent_color": "#F59E0B",
            "font_style": "clean",
            "density": "comfortable",
        },
    }
