"""The common SourceRecord contract shared by every SourceAdapter.

Field list and physical storage layout per
docs/data_pipeline/SOURCE_ADAPTER_SPEC_MVP.md §1.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SourceRecord:
    source_record_id: str
    source: str
    source_job_id: str | None
    source_url: str | None
    resolved_url: str | None
    collection_run_id: str
    sourcing_config_version: str
    source_config_id: str
    query_group_id: str
    query_id: str
    query_text_or_parameters: str
    captured_at: str
    adapter_version: str
    parser_version: str
    capture_method: str
    raw_title: str | None
    raw_company: str | None
    raw_location: Any
    raw_description: str | None
    raw_publication_date: str | None
    raw_job_status: Any
    raw_work_mode: Any
    raw_payload_reference: str
    content_hash: str
    collection_status: str
    parser_warnings: list[str] = field(default_factory=list)
    error_code: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), default=str, ensure_ascii=False)


def compute_content_hash(*, title: str | None, company: str | None,
                          location: Any, description: str | None,
                          publication_date: str | None) -> str:
    """Deterministic fingerprint of the fields that define "the same content".

    Not pinned by any spec doc (JOB_SCHEMA_MVP.md only shows a
    64-hex-char sample); sha256 over a sorted-key JSON projection of the
    content-bearing fields is this adapter layer's choice, not the schema's.
    """
    payload = {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "publication_date": publication_date,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
