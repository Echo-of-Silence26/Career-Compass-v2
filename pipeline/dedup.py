"""Layer 1 (intra-source) pre-extraction deduplication.

Per docs/data_pipeline/DEDUPLICATION_SPEC_MVP.md §2: scans only the same
source's own data/raw/source_records/{source}.jsonl, matches on
source + source_job_id (fallback: source_url), compares content_hash.
Layer 2 (cross-source candidate matching) is explicitly post-MVP and not
implemented here.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.source_record import SourceRecord

DEFAULT_RAW_DIR = Path("data/raw/source_records")


class RawJobDeduplicator:
    def __init__(self, raw_dir: Path = DEFAULT_RAW_DIR):
        self.raw_dir = raw_dir

    def _identity(self, record: SourceRecord) -> str:
        if record.source_job_id:
            return f"{record.source}::id::{record.source_job_id}"
        # Fallback identity per DEDUPLICATION_SPEC_MVP.md §2.1 -- if neither
        # source_job_id nor resolved_url is available, the record cannot be
        # identity-matched at all and must be treated as `new` (§2.1 point 3),
        # never silently dropped.
        if record.resolved_url:
            return f"{record.source}::url::{record.resolved_url}"
        return f"{record.source}::none::{record.source_record_id}"

    def classify(self, record: SourceRecord) -> str:
        """Return 'new', 'duplicate_unchanged', or 'changed'.

        Must be called *before* the current record is appended to the raw
        JSONL file -- it scans prior persisted records only, per
        DEDUPLICATION_SPEC_MVP.md §2.2 (same-source file, no cross-file glob).
        """
        path = self.raw_dir / f"{record.source.lower()}.jsonl"
        if not path.exists():
            return "new"

        target_identity = self._identity(record)
        # Records without any stable identity (fallback branch above) always
        # compare unequal to themselves across calls, so they always come
        # back "new" -- consistent with §2.1 point 3's "never silently drop".
        if target_identity.endswith(f"::none::{record.source_record_id}"):
            return "new"

        latest_hash: str | None = None
        found = False
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                prior = json.loads(line)
                prior_identity = self._prior_identity(prior)
                if prior_identity == target_identity:
                    found = True
                    latest_hash = prior.get("content_hash")

        if not found:
            return "new"
        if latest_hash == record.content_hash:
            return "duplicate_unchanged"
        return "changed"

    def _prior_identity(self, prior: dict) -> str:
        source = prior.get("source")
        source_job_id = prior.get("source_job_id")
        if source_job_id:
            return f"{source}::id::{source_job_id}"
        resolved_url = prior.get("resolved_url")
        if resolved_url:
            return f"{source}::url::{resolved_url}"
        return f"{source}::none::{prior.get('source_record_id')}"
