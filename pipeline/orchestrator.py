"""Pipeline Orchestrator: wires every stage in order.

discover -> capture/persist raw -> dedup -> extract -> eligibility guard ->
Hard Disqualifier -> Capability Fit (if not excluded) -> assemble + persist
-> reconcile -> Excel export, per
docs/data_pipeline/MVP_WORKFLOW_STAGE_CONTRACT_MAP.md.

Implements the "small initial manual checkpoint" from EVAL_EXECUTION_PROMPT.md
§6: after the first non-duplicate job's full result is produced, print it and
prompt before continuing the batch. Per-job failures are caught and recorded
with stage + reason -- they never crash the run (MVP Acceptance Criterion 11).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from pipeline.adapters.indeed_apify import IndeedApifyAdapter
from pipeline.adapters.linkedin_apify import LinkedInApifyAdapter
from pipeline.assessment_schema import (
    CapabilityFitResult,
    HardDisqualifierResult,
    EvaluationResult,
)
from pipeline.candidate_profile import CandidateProfile
from pipeline.capability_fit import CapabilityFitEvaluator
from pipeline.dedup import RawJobDeduplicator
from pipeline.eligibility import AssessmentEligibilityChecker
from pipeline.hard_disqualifier import HardDisqualifierEvaluator
from pipeline.job_extractor import ExtractionFailure, JobExtractor
from pipeline.job_schema import Job
from pipeline.llm_common import AssessmentCallFailure
from pipeline.model_config import ModelConfigCatalog
from pipeline.query_catalog import QueryCatalog
from pipeline.raw_job_repository import RawJobRepository
from pipeline.reconciliation import RunReconciler
from pipeline.result_repository import EvaluationRepository, JobRepository
from pipeline.review_export import HumanReviewExporter
from pipeline.run_manifest import RunManifest
from pipeline.source_adapter import LocationFilter, QueryDefinition, RunContext, SourceAdapter
from pipeline.source_record import SourceRecord, utcnow_iso

EVAL_EXECUTION_PROMPT_VERSION = "eval-execution-v0.2"

SOURCE_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "Indeed": IndeedApifyAdapter,
    "LinkedIn": LinkedInApifyAdapter,
}


class ManualCheckpointStop(Exception):
    """Raised when the user declines to continue past the manual checkpoint."""


class PipelineOrchestrator:
    def __init__(self, *, manifest: RunManifest, candidate_profile: CandidateProfile,
                 query_catalog: QueryCatalog, location: LocationFilter,
                 model_config_catalog: ModelConfigCatalog | None = None,
                 interactive: bool = True):
        self.manifest = manifest
        self.candidate_profile = candidate_profile
        self.query_catalog = query_catalog
        self.location = location
        self.interactive = interactive
        self._checkpoint_done = not interactive

        model_config_catalog = model_config_catalog or ModelConfigCatalog()
        self.model_config_catalog = model_config_catalog

        self.raw_repo = RawJobRepository()
        self.job_repo = JobRepository()
        self.eval_repo = EvaluationRepository()
        self.reconciler = RunReconciler()
        self.dedup = RawJobDeduplicator()

        extraction_cfg = model_config_catalog.stage_config("extraction")
        hd_cfg = model_config_catalog.stage_config("hard_disqualifier")
        fit_cfg = model_config_catalog.stage_config("capability_fit")

        self.extractor = JobExtractor(
            model_config_catalog.build_client("extraction"),
            max_tokens=extraction_cfg.max_tokens, temperature=extraction_cfg.temperature,
            query_catalog=query_catalog,
        )
        self.hd_evaluator = HardDisqualifierEvaluator(
            model_config_catalog.build_client("hard_disqualifier"),
            max_tokens=hd_cfg.max_tokens, temperature=hd_cfg.temperature,
        )
        self.fit_evaluator = CapabilityFitEvaluator(
            model_config_catalog.build_client("capability_fit"),
            max_tokens=fit_cfg.max_tokens, temperature=fit_cfg.temperature,
        )
        self._hd_model_identifier = hd_cfg.model

    def run(self) -> None:
        # Use the manifest's own run_id as THE run identity everywhere (raw
        # capture, Job records, evaluation results, reconciliation summary) --
        # RunContext.new() would mint a second, different run_id, which would
        # silently desync raw-capture provenance from the evaluation results
        # keyed by manifest.run_id in _finish().
        run_context = RunContext(run_id=self.manifest.run_id,
                                  sourcing_config_version=self.manifest.sourcing_config_version)
        active_queries = self.query_catalog.active()

        for source in self.manifest.sources_enabled:
            adapter_cls = SOURCE_ADAPTERS[source]
            adapter = adapter_cls()
            remaining = self.manifest.max_jobs_per_source

            for query in active_queries:
                if query.role_family not in self._role_families_for_source():
                    continue
                if remaining is not None and remaining <= 0:
                    break
                max_rows = remaining  # None means no quantity cap, including per query.
                query_def = QueryDefinition(
                    query_id=query.query_id, query_group_id=query.query_group_id,
                    term=query.term, language=query.language,
                )
                records = adapter.capture(query_def, self.location, run_context, max_rows)
                for record in records:
                    if remaining is not None and remaining <= 0:
                        break
                    try:
                        self._process_record(record, run_context.run_id)
                    except ManualCheckpointStop:
                        self._finish()
                        return
                    if remaining is not None:
                        remaining -= 1

        self._finish()

    def _role_families_for_source(self) -> set[str]:
        # MVP scope has no per-source role-family restriction beyond the
        # shared query set (SOURCING_POLICY_MVP.md) -- every active
        # role family is eligible on every enabled source.
        return {q.role_family for q in self.query_catalog.active()}

    def _process_record(self, record: SourceRecord, run_id: str) -> None:
        c = self.reconciler.counts
        c.discovered += 1

        outcome = self.dedup.classify(record)  # must run before append (scans prior records only)
        self.raw_repo.append(record)
        c.captured += 1

        if outcome == "duplicate_unchanged":
            c.duplicate_unchanged += 1
            return
        c.new += 1 if outcome == "new" else 0
        c.changed += 1 if outcome == "changed" else 0

        extraction_result = self.extractor.extract(record)
        if isinstance(extraction_result, ExtractionFailure):
            c.extraction_failed += 1
            c.needs_human_review += 1
            print(f"[extraction FAILED] {record.raw_title!r} @ {record.source_url}: "
                  f"{extraction_result.reason}")
            return

        job = extraction_result
        self.job_repo.append(job)

        eligibility = AssessmentEligibilityChecker().check(job, record, self.manifest)
        if eligibility.assessment_eligibility == "Blocked":
            c.blocked += 1
            c.needs_human_review += 1
            result = self._build_result(
                run_id=run_id, job=job, input_status="Blocked",
                blocking_reasons=eligibility.blocking_reasons,
                hard_disqualifier=HardDisqualifierResult(), capability_fit=CapabilityFitResult(),
                fit_skip_reason=None, evaluation_status="Blocked",
                failure_stage=None, failure_reason=None,
            )
            self.eval_repo.append(result)
            self._maybe_checkpoint(job, result)
            return

        hd_result = self.hd_evaluator.evaluate(job, record.raw_description, self.candidate_profile)
        if isinstance(hd_result, AssessmentCallFailure):
            c.evaluation_failed += 1
            c.needs_human_review += 1
            result = self._build_result(
                run_id=run_id, job=job, input_status="Eligible", blocking_reasons=[],
                hard_disqualifier=HardDisqualifierResult(), capability_fit=CapabilityFitResult(),
                fit_skip_reason=None, evaluation_status="Failed",
                failure_stage="HardDisqualifier", failure_reason=hd_result.reason,
            )
            self.eval_repo.append(result)
            self._maybe_checkpoint(job, result)
            return

        any_fail = any(r.state == "Fail" for r in hd_result.rules)
        needs_review_hd = any(r.state in ("Flag", "Unknown") for r in hd_result.rules)

        if any_fail:
            c.hard_disqualifier_excluded += 1
            if needs_review_hd:
                c.needs_human_review += 1
            result = self._build_result(
                run_id=run_id, job=job, input_status="Eligible", blocking_reasons=[],
                hard_disqualifier=hd_result, capability_fit=CapabilityFitResult(),
                fit_skip_reason="HardDisqualifierFail", evaluation_status="Completed",
                failure_stage=None, failure_reason=None,
            )
            self.eval_repo.append(result)
            self._maybe_checkpoint(job, result)
            return

        fit_result = self.fit_evaluator.evaluate(job, record.raw_description, self.candidate_profile)
        if isinstance(fit_result, AssessmentCallFailure):
            c.evaluation_failed += 1
            c.needs_human_review += 1
            result = self._build_result(
                run_id=run_id, job=job, input_status="Eligible", blocking_reasons=[],
                hard_disqualifier=hd_result, capability_fit=CapabilityFitResult(),
                fit_skip_reason=None, evaluation_status="Failed",
                failure_stage="CapabilityFit", failure_reason=fit_result.reason,
            )
            self.eval_repo.append(result)
            self._maybe_checkpoint(job, result)
            return

        c.fit_completed += 1
        if needs_review_hd or fit_result.label == "Unclear":
            c.needs_human_review += 1

        result = self._build_result(
            run_id=run_id, job=job, input_status="Eligible", blocking_reasons=[],
            hard_disqualifier=hd_result, capability_fit=fit_result,
            fit_skip_reason=None, evaluation_status="Completed",
            failure_stage=None, failure_reason=None,
        )
        self.eval_repo.append(result)
        self._maybe_checkpoint(job, result)

    def _build_result(self, *, run_id: str, job: Job, input_status: str,
                       blocking_reasons: list[str], hard_disqualifier: HardDisqualifierResult,
                       capability_fit: CapabilityFitResult, fit_skip_reason: str | None,
                       evaluation_status: str, failure_stage: str | None,
                       failure_reason: str | None) -> EvaluationResult:
        return EvaluationResult(
            evaluation_id=f"eval_{uuid.uuid4().hex}",
            job_id=job.job_id, run_id=run_id,
            # Identity fields can be missing on an input that was deliberately
            # routed to Blocked by the eligibility guard.  The evaluation
            # envelope keeps these fields as strings, so preserve the missing
            # value as an empty string instead of crashing before the Blocked
            # result can be recorded for human review.
            company=job.company or "", title=job.title or "", source_url=job.source_url,
            job_content_hash=job.content_hash or "",
            candidate_profile_version=self.manifest.candidate_profile_version,
            input_status=input_status, blocking_reasons=blocking_reasons,
            hard_disqualifier=hard_disqualifier, capability_fit=capability_fit,
            fit_skip_reason=fit_skip_reason,
            evaluation_status=evaluation_status, failure_stage=failure_stage,
            failure_reason=failure_reason,
            prompt_version=EVAL_EXECUTION_PROMPT_VERSION,
            model_identifier=self._hd_model_identifier,
            model_config_version=self.manifest.model_config_version,
            output_schema_version=self.manifest.output_schema_version,
            evaluated_at=utcnow_iso(),
        )

    def _maybe_checkpoint(self, job: Job, result: EvaluationResult) -> None:
        if self._checkpoint_done:
            return
        self._checkpoint_done = True
        print("=" * 70)
        print("MANUAL CHECKPOINT -- first processed job, full result:")
        print(f"Job: {job.company} / {job.title} ({job.source_url})")
        print(result.model_dump_json(indent=2))
        print("=" * 70)
        answer = input("Continue processing the rest of the batch? [y/N] ").strip().lower()
        if answer != "y":
            print("Stopping at manual checkpoint per user request.")
            raise ManualCheckpointStop()

    def _finish(self) -> None:
        summary_path = self.reconciler.write_summary(self.manifest.run_id)
        print(f"\nRun {self.manifest.run_id} finished. Summary: {summary_path}")
        print(self.reconciler.counts)
        problems = self.reconciler.reconcile()
        if problems:
            print("RECONCILIATION PROBLEMS:")
            for p in problems:
                print(f"- {p}")

        all_results = self.eval_repo.read_all_for_run(self.manifest.run_id)
        jobs_by_id = self.job_repo.read_current()
        export_path = Path(f"data/runs/{self.manifest.run_id}/review_export.xlsx")
        HumanReviewExporter().export(all_results, jobs_by_id, export_path)
        print(f"Human review export: {export_path}")
