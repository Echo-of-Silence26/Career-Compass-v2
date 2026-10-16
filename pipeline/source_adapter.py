"""SourceAdapter interface, plus the two run-scoped inputs every adapter needs.

RunContext stubs the Stage 0 run manifest, which
docs/data_pipeline/MVP_WORKFLOW_STAGE_CONTRACT_MAP.md row 0 lists as
"Missing P0: command, manifest, checkpoint, and terminal-state contract" —
this is a placeholder run_id so RawJobRecord.collection_run_id is populated
today, not a stand-in for that future design.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from pipeline.source_record import SourceRecord, utcnow_iso


@dataclass
class RunContext:
    run_id: str
    sourcing_config_version: str

    @classmethod
    def new(cls, sourcing_config_version: str) -> "RunContext":
        return cls(run_id=f"run-{utcnow_iso()}-{uuid.uuid4().hex[:8]}",
                    sourcing_config_version=sourcing_config_version)


@dataclass
class QueryDefinition:
    """One row from config/sourcing/queries-v0.1.yaml."""
    query_id: str
    query_group_id: str
    term: str
    language: str


@dataclass
class LocationFilter:
    """The candidate_base geography a query is executed against."""
    city: str
    country_code: str


class SourceAdapter(ABC):
    """Common capture interface every source implements.

    Must not perform Candidate Profile matching, Capability Fit filtering,
    or application recommendation (SOURCE_ADAPTER_SPEC_MVP.md §1).
    """

    source: str
    source_config_id: str
    adapter_version: str
    parser_version: str
    capture_method: str

    @abstractmethod
    def capture(self, query: QueryDefinition, location: LocationFilter,
                run_context: RunContext, max_rows: int | None) -> list[SourceRecord]:
        """Run discovery+detail capture for one query and return SourceRecords."""
        raise NotImplementedError
