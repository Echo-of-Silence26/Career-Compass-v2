"""Minimal Assessment Eligibility guard.

Per docs/data_pipeline/DATA_PIPELINE_MVP_SPEC.md §4.3.1: structural checks
only (parseable identity, non-empty required strings, required versions
present). Does NOT check full schema conformance, semantic completeness, or
description-URL/company/title mismatch -- those are deferred Data Validation
checks, out of scope for the first runnable MVP.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.job_schema import Job
from pipeline.run_manifest import RunManifest
from pipeline.source_record import SourceRecord, utcnow_iso

ELIGIBILITY_RULES_VERSION = "assessment-eligibility-v0.1"

REQUIRED_NON_EMPTY_FIELDS = ("description", "responsibilities", "qualifications_requirements")


@dataclass
class EligibilityResult:
    assessment_eligibility: str  # Eligible | Blocked
    eligibility_rules_version: str
    blocking_reasons: list[str] = field(default_factory=list)
    checked_at: str = ""


class AssessmentEligibilityChecker:
    def check(self, job: Job, raw_record: SourceRecord, manifest: RunManifest) -> EligibilityResult:
        reasons: list[str] = []

        if not (job.job_id and job.title and job.company and job.source_url and job.captured_at):
            reasons.append(
                "Missing traceable job identity (job_id/title/company/source_url/captured_at)"
            )

        if not raw_record.raw_description or not raw_record.content_hash:
            reasons.append("Raw JD evidence or content hash unavailable")

        for field_name in REQUIRED_NON_EMPTY_FIELDS:
            value = getattr(job, field_name)
            if not value or not value.strip():
                reasons.append(f"Required field '{field_name}' is missing or empty")

        required_versions = {
            "Candidate Profile version": manifest.candidate_profile_version,
            "Hard Disqualifier policy version": manifest.hard_disqualifier_policy_version,
            "Capability Fit policy version": manifest.capability_fit_policy_version,
            "extraction prompt version": manifest.extraction_prompt_version,
            "output schema version": manifest.output_schema_version,
        }
        for label, value in required_versions.items():
            if not value:
                reasons.append(f"Missing {label}")

        return EligibilityResult(
            assessment_eligibility="Blocked" if reasons else "Eligible",
            eligibility_rules_version=ELIGIBILITY_RULES_VERSION,
            blocking_reasons=reasons,
            checked_at=utcnow_iso(),
        )
