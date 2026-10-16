"""Append-only JSONL persistence for SourceRecords.

Physical layout per SOURCE_ADAPTER_SPEC_MVP.md §1: one file per source,
data/raw/source_records/{source}.jsonl, append-only, never rewritten.
data/raw/ is already gitignored.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.source_record import SourceRecord

DEFAULT_RAW_DIR = Path("data/raw/source_records")


class RawJobRepository:
    def __init__(self, base_dir: Path = DEFAULT_RAW_DIR):
        self.base_dir = base_dir

    def _path_for(self, source: str) -> Path:
        return self.base_dir / f"{source.lower()}.jsonl"

    def append(self, record: SourceRecord) -> Path:
        path = self._path_for(record.source)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(record.to_json_line() + "\n")
        return path
