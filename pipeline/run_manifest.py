"""Minimal Stage-0 run manifest.

Resolves the "Missing P0: command, manifest, checkpoint, and terminal-state
contract" gap flagged in docs/data_pipeline/MVP_WORKFLOW_STAGE_CONTRACT_MAP.md
row 0, scoped to exactly what the current pipeline stages need to record --
not the full parked CollectionBatch/CollectionRun state machine
(DATA_PIPELINE_MVP_SPEC.md §5).

Per docs/data_pipeline/MODEL_CONFIG_MVP.md, provider/model/params live in
config/models/model-config-v0.1.yaml, not here -- the manifest only records
which model_config_version a run used, for traceability.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from pipeline.source_record import utcnow_iso


def _new_run_id() -> str:
    # Filesystem-safe (no colons) unlike utcnow_iso()'s raw ISO 8601 --
    # run_id is used directly as a data/runs/{run_id} directory name.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run-{stamp}-{uuid.uuid4().hex[:8]}"


@dataclass
class RunManifest:
    run_id: str
    started_at: str

    sourcing_config_version: str
    candidate_profile_version: str
    hard_disqualifier_policy_version: str
    capability_fit_policy_version: str
    extraction_prompt_version: str
    output_schema_version: str
    model_config_version: str

    sources_enabled: list[str]
    # None means no business result cap. Source adapters still apply a
    # separately configured technical spend guard.
    max_jobs_per_source: int | None

    @classmethod
    def new(
        cls,
        *,
        sourcing_config_version: str,
        candidate_profile_version: str,
        hard_disqualifier_policy_version: str,
        capability_fit_policy_version: str,
        extraction_prompt_version: str,
        output_schema_version: str,
        model_config_version: str,
        sources_enabled: list[str],
        max_jobs_per_source: int | None,
    ) -> "RunManifest":
        return cls(
            run_id=_new_run_id(),
            started_at=utcnow_iso(),
            sourcing_config_version=sourcing_config_version,
            candidate_profile_version=candidate_profile_version,
            hard_disqualifier_policy_version=hard_disqualifier_policy_version,
            capability_fit_policy_version=capability_fit_policy_version,
            extraction_prompt_version=extraction_prompt_version,
            output_schema_version=output_schema_version,
            model_config_version=model_config_version,
            sources_enabled=sources_enabled,
            max_jobs_per_source=max_jobs_per_source,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, ensure_ascii=False, indent=2)
