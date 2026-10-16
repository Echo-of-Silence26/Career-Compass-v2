"""The canonical MVP `Job` contract.

Field list, enums, and processing rules per
docs/data_pipeline/JOB_SCHEMA_MVP.md. Layer 2 (cross-source
duplicate candidate matching) is post-MVP per DEDUPLICATION_SPEC_MVP.md §1,
so `duplicate_candidates`/`duplicate_status` are always written at their
schema defaults ([] / "Unreviewed") here -- nothing populates them yet.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DuplicateCandidate:
    job_id: str
    source_url: str
    match_basis: str  # IntraSourceWeakFallback | CrossSourceStrong | CrossSourceWeak
    confidence: str  # Strong | Weak


@dataclass
class Job:
    job_id: str

    source: str  # Indeed | LinkedIn
    source_job_id: str | None
    source_url: str

    matched_search_terms: list[str]

    role_family: str  # CustomerSuccess | Growth | Marketing | ITProjectManagement

    company: str
    title: str

    city: str | None
    country: str | None

    work_mode: str  # Remote | Hybrid | OnSite | Unknown

    description: str | None
    responsibilities: str | None
    qualifications_requirements: str | None

    description_status: str  # Full | Partial | Missing

    published_at: str | None

    content_hash: str | None

    captured_at: str
    updated_at: str

    duplicate_candidates: list[DuplicateCandidate] = field(default_factory=list)
    duplicate_status: str = "Unreviewed"

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), default=str, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Job":
        d = dict(d)
        candidates = [DuplicateCandidate(**c) for c in d.get("duplicate_candidates", [])]
        d["duplicate_candidates"] = candidates
        return cls(**d)
