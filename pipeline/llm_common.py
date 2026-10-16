"""Shared helpers for the two assessment LLM callers (HD and Fit).

Loads frozen policy/prompt doc text straight from the docs/ files at runtime
(never duplicated into code, so the frozen policy stays the single source of
truth -- see the ADR pattern). The actual model call goes through
pipeline/model_client.py's ModelClient interface, not through anything here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AssessmentCallFailure:
    stage: str  # "HardDisqualifier" | "CapabilityFit"
    reason: str
    raw_response_text: str | None = None


def read_doc(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
