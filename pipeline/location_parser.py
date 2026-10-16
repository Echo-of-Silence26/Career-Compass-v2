"""Deterministic city/country extraction from each source's raw_location shape.

Indeed's raw_location (via the Apify actor) is already a structured object
with city/country keys -- pure passthrough, no parsing. LinkedIn's is a single
free-text "City, Region, Country" string -- comma-split. Per
JOB_EXTRACTION_PROMPT_MVP.md §2, this is an address-formatting difference, not
JD content requiring semantic interpretation, so it belongs here rather than
in the extraction LLM call.
"""

from __future__ import annotations

from typing import Any


def parse_location(source: str, raw_location: Any) -> tuple[str | None, str | None]:
    """Return (city, country). Never guesses; missing/unparseable -> (None, None)."""
    if source == "Indeed":
        return _parse_indeed(raw_location)
    if source == "LinkedIn":
        return _parse_linkedin(raw_location)
    return (None, None)


def _parse_indeed(raw_location: Any) -> tuple[str | None, str | None]:
    if not isinstance(raw_location, dict):
        return (None, None)
    city = raw_location.get("city") or None
    country = raw_location.get("country") or None
    return (city, country)


def _parse_linkedin(raw_location: Any) -> tuple[str | None, str | None]:
    if not isinstance(raw_location, str) or not raw_location.strip():
        return (None, None)
    parts = [p.strip() for p in raw_location.split(",") if p.strip()]
    if not parts:
        return (None, None)
    if len(parts) == 1:
        # A single token (e.g. "Remote") has no separate country -- keep it as
        # the city value rather than guessing which it is.
        return (parts[0], None)
    return (parts[0], parts[-1])
