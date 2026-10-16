"""Offline smoke test for the Phase A deterministic components.

Zero network/API calls. Exercises location_parser, RawJobDeduplicator,
AssessmentEligibilityChecker, CandidateProfile loading, and the
assessment_schema cross-field validation rules against the saved Apify
fixtures and a scratch raw-record directory (deleted after the run).

Run: python -m pipeline.validate_phase_a
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from pipeline.assessment_schema import EvaluationResult
from pipeline.candidate_profile import CandidateProfile
from pipeline.dedup import RawJobDeduplicator
from pipeline.eligibility import AssessmentEligibilityChecker
from pipeline.job_schema import Job
from pipeline.location_parser import parse_location
from pipeline.run_manifest import RunManifest
from pipeline.source_record import SourceRecord, compute_content_hash, utcnow_iso

INDEED_FIXTURE = Path("data/private/fixtures/indeed_apify/apify_probe_raw_2026-08-31.json")
LINKEDIN_FIXTURE = Path("data/private/fixtures/linkedin/apify_probe_raw_2026-08-31.json")

problems: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


def test_location_parser() -> None:
    indeed_items = json.loads(INDEED_FIXTURE.read_text())
    city, country = parse_location("Indeed", indeed_items[0]["location"])
    check(city == "München", f"Indeed city parse: expected 'München', got {city!r}")
    check(country == "Deutschland", f"Indeed country parse: expected 'Deutschland', got {country!r}")

    linkedin_items = json.loads(LINKEDIN_FIXTURE.read_text())
    city, country = parse_location("LinkedIn", linkedin_items[0]["location"])
    check(city == "Munich", f"LinkedIn city parse: expected 'Munich', got {city!r}")
    check(country == "Germany", f"LinkedIn country parse: expected 'Germany', got {country!r}")

    city, country = parse_location("LinkedIn", "Remote")
    check(city == "Remote" and country is None, f"single-token LinkedIn location: got {(city, country)!r}")

    city, country = parse_location("Indeed", None)
    check(city is None and country is None, "missing Indeed location should be (None, None)")


def _make_source_record(source: str, source_job_id: str, content_hash: str) -> SourceRecord:
    return SourceRecord(
        source_record_id="rec-1",
        source=source,
        source_job_id=source_job_id,
        source_url="https://example.com/job/1",
        resolved_url="https://example.com/job/1",
        collection_run_id="run-test",
        sourcing_config_version="sourcing-config-v0.1",
        source_config_id="indeed-de-v0.1",
        query_group_id="customer-success-v0.1",
        query_id="cs-customer-success-manager-en-v0.1",
        query_text_or_parameters="Customer Success Manager",
        captured_at=utcnow_iso(),
        adapter_version="indeed-apify-v0.1",
        parser_version="indeed-apify-direct-mapping-v0.1",
        capture_method="ApifyActor",
        raw_title="Customer Success Manager",
        raw_company="Acme",
        raw_location={"city": "München", "country": "Deutschland"},
        raw_description="A job description.",
        raw_publication_date="2026-09-01",
        raw_job_status=False,
        raw_work_mode=False,
        raw_payload_reference="inline",
        content_hash=content_hash,
        collection_status="Success",
    )


def test_dedup(tmp_dir: Path) -> None:
    dedup = RawJobDeduplicator(raw_dir=tmp_dir)
    record_v1 = _make_source_record("Indeed", "job-123", "hash-a")

    check(dedup.classify(record_v1) == "new", "first sighting of job-123 should be 'new'")

    # Persist it (mimicking RawJobRepository.append) before checking again.
    path = tmp_dir / "indeed.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(record_v1.to_json_line() + "\n")

    record_same = _make_source_record("Indeed", "job-123", "hash-a")
    check(dedup.classify(record_same) == "duplicate_unchanged",
          "same content_hash for known job-123 should be 'duplicate_unchanged'")

    record_changed = _make_source_record("Indeed", "job-123", "hash-b")
    check(dedup.classify(record_changed) == "changed",
          "different content_hash for known job-123 should be 'changed'")

    record_other = _make_source_record("Indeed", "job-999", "hash-c")
    check(dedup.classify(record_other) == "new", "a different job_id should be 'new'")

    # Fallback identity: no source_job_id, no resolved_url -> always 'new', never dropped.
    record_no_id = _make_source_record("Indeed", None, "hash-d")
    record_no_id.resolved_url = None
    check(dedup.classify(record_no_id) == "new",
          "a record with no source_job_id and no resolved_url should be 'new'")


def _make_job(**overrides) -> Job:
    base = dict(
        job_id="job_test_1",
        source="Indeed",
        source_job_id="job-123",
        source_url="https://example.com/job/1",
        matched_search_terms=["Customer Success Manager"],
        role_family="CustomerSuccess",
        company="Acme",
        title="Customer Success Manager",
        city="München",
        country="Deutschland",
        work_mode="Hybrid",
        description="A role.",
        responsibilities="Manage accounts.",
        qualifications_requirements="3 years experience.",
        description_status="Full",
        published_at="2026-09-01",
        content_hash="hash-a",
        captured_at=utcnow_iso(),
        updated_at=utcnow_iso(),
    )
    base.update(overrides)
    return Job(**base)


def test_eligibility() -> None:
    checker = AssessmentEligibilityChecker()
    record = _make_source_record("Indeed", "job-123", "hash-a")
    manifest = RunManifest.new(
        sourcing_config_version="sourcing-config-v0.1",
        candidate_profile_version="candidate-profile-v0.1",
        hard_disqualifier_policy_version="hard-disqualifier-v0.2",
        capability_fit_policy_version="capability-fit-v0.3",
        extraction_prompt_version="job-extraction-v0.1",
        output_schema_version="eval-result-v0.2",
        model_config_version="mvp-model-config-v0.1",
        sources_enabled=["Indeed"],
        max_jobs_per_source=1,
    )

    good_job = _make_job()
    result = checker.check(good_job, record, manifest)
    check(result.assessment_eligibility == "Eligible", f"complete job should be Eligible, got {result.blocking_reasons}")

    bad_job = _make_job(responsibilities="   ")
    result = checker.check(bad_job, record, manifest)
    check(result.assessment_eligibility == "Blocked", "empty responsibilities should be Blocked")
    check(any("responsibilities" in r for r in result.blocking_reasons),
          f"blocking reason should mention responsibilities, got {result.blocking_reasons}")


def test_candidate_profile() -> None:
    profile = CandidateProfile.load()
    check(profile.version == "candidate-profile-v0.1", f"unexpected profile version {profile.version}")
    check(len(profile.content_hash) == 64, "content_hash should be a sha256 hex digest")
    check("evidence_items" in profile.data, "profile data missing evidence_items")
    text = profile.as_prompt_text()
    check(len(text) > 100, "as_prompt_text() rendered suspiciously short output")


def test_assessment_schema() -> None:
    # A valid HD-Fail result.
    fail_result = EvaluationResult(
        evaluation_id="eval-1", job_id="job_test_1", run_id="run-test",
        company="Acme", title="Customer Success Manager", source_url="https://example.com/job/1",
        job_content_hash="hash-a", candidate_profile_version="candidate-profile-v0.1",
        input_status="Eligible", blocking_reasons=[],
        hard_disqualifier={
            "policy_version": "hard-disqualifier-v0.2",
            "rules": [{"rule_id": "3.1(b)", "rule_name": "senior_years", "state": "Fail",
                       "evidence_quote": "5+ years required", "candidate_evidence": None,
                       "reason": "Explicit 5-year floor."}],
            "overall_decision": "Exclude",
        },
        capability_fit={"policy_version": None, "label": None, "skills": [], "core_skills": [], "evidence": [], "unknowns": []},
        fit_skip_reason="HardDisqualifierFail",
        evaluation_status="Completed", failure_stage=None, failure_reason=None,
        prompt_version="eval-execution-v0.2", model_identifier="claude-sonnet-5",
        model_config_version="v1", evaluated_at=utcnow_iso(),
    )
    check(fail_result.hard_disqualifier.overall_decision == "Exclude", "HD-Fail fixture should round-trip")

    # An invalid result: a Fail rule but overall_decision left as ProceedToCapabilityFit.
    try:
        EvaluationResult(
            evaluation_id="eval-2", job_id="job_test_1", run_id="run-test",
            company="Acme", title="X", source_url="https://example.com/job/1",
            job_content_hash="hash-a", candidate_profile_version="candidate-profile-v0.1",
            input_status="Eligible", blocking_reasons=[],
            hard_disqualifier={
                "policy_version": "hard-disqualifier-v0.2",
                "rules": [{"rule_id": "3.1(b)", "rule_name": "senior_years", "state": "Fail",
                           "evidence_quote": "5+ years", "candidate_evidence": None, "reason": "x"}],
                "overall_decision": "ProceedToCapabilityFit",
            },
            capability_fit={"policy_version": None, "label": None, "skills": [], "core_skills": [], "evidence": [], "unknowns": []},
            fit_skip_reason=None,
            evaluation_status="Completed", failure_stage=None, failure_reason=None,
            prompt_version="eval-execution-v0.2", model_identifier="claude-sonnet-5",
            model_config_version="v1", evaluated_at=utcnow_iso(),
        )
        problems.append("expected ValueError for Fail+ProceedToCapabilityFit inconsistency, none raised")
    except Exception:
        pass  # expected

    def fit_result(capability_fit: dict) -> EvaluationResult:
        return EvaluationResult(
            evaluation_id="eval-3", job_id="job_test_1", run_id="run-test",
            company="Acme", title="X", source_url="https://example.com/job/1",
            job_content_hash="hash-a", candidate_profile_version="candidate-profile-v0.1",
            input_status="Eligible", blocking_reasons=[],
            hard_disqualifier={"policy_version": "hard-disqualifier-v0.2", "rules": [], "overall_decision": "ProceedToCapabilityFit"},
            capability_fit=capability_fit,
            fit_skip_reason=None,
            evaluation_status="Completed", failure_stage=None, failure_reason=None,
            prompt_version="eval-execution-v0.2", model_identifier="claude-sonnet-5",
            model_config_version="v1", evaluated_at=utcnow_iso(),
        )

    skills = [
        {"skill_id": "S1", "skill": "B2B account management", "category": "method",
         "jd_signal": "required", "jd_quote": "Own B2B accounts"},
        {"skill_id": "S2", "skill": "Customer onboarding programme design", "category": "method",
         "jd_signal": "responsibility", "jd_quote": "Run onboarding"},
        {"skill_id": "S3", "skill": "CRM platform", "category": "tool",
         "jd_signal": "required", "jd_quote": "HubSpot or similar"},
        {"skill_id": "S4", "skill": "SQL", "category": "tool",
         "jd_signal": "preferred", "jd_quote": "SQL is a plus"},
    ]
    core_skills = [{"skill_id": "S1", "reason": "Central function."},
                   {"skill_id": "S2", "reason": "Primary responsibility."},
                   {"skill_id": "S3", "reason": "Campaigns run through it."}]
    evidence = [
        {"skill_id": "S1", "state": "done", "candidate_evidence": "ev-01",
         "scope": "Owned two named accounts.", "shifted_dimensions": [],
         "reasoning": "Owned B2B accounts end-to-end."},
        {"skill_id": "S2", "state": "adjacent", "candidate_evidence": "ev-01",
         "scope": None, "shifted_dimensions": ["object"], "reasoning": "Programme launches transfer."},
        {"skill_id": "S3", "state": "participated", "candidate_evidence": "ev-02",
         "scope": "Used the CRM; admin owned by ops.", "shifted_dimensions": [],
         "reasoning": "Daily CRM user; no admin ownership."},
        {"skill_id": "S4", "state": "unconfirmed", "candidate_evidence": None,
         "scope": None, "shifted_dimensions": [], "reasoning": "No SQL in the CV. Any hands-on?"},
    ]
    industry = {"industry": "B2B SaaS", "jd_signal": "context_only", "jd_quote": "our SaaS platform"}
    industry_evidence = {"state": "done", "candidate_evidence": "ev-01",
                         "scope": "Worked two years in B2B SaaS.", "shifted_dimensions": [],
                         "reasoning": "Two years in B2B SaaS."}
    base_fit = {"policy_version": "capability-fit-v0.3", "label": "PlausibleFit",
                "skills": skills, "core_skills": core_skills, "industry": industry,
                "evidence": evidence, "industry_evidence": industry_evidence, "unknowns": []}

    # A valid Fit result round-trips (non-core S4 unconfirmed doesn't affect the label).
    try:
        fit_result(base_fit)
    except Exception as e:
        problems.append(f"valid v0.3 Fit result was rejected: {e}")

    def with_evidence(index: int, **changes) -> dict:
        changed = [dict(e) for e in evidence]
        changed[index].update(changes)
        return {**base_fit, "evidence": changed}

    invalid_cases = {
        "adjacent evidence missing shifted_dimensions": with_evidence(1, shifted_dimensions=[]),
        "done evidence missing its responsibility scope": with_evidence(0, scope=None),
        "not_done without citing an explicit profile statement": {
            **with_evidence(3, state="not_done"), "label": "PlausibleFit"},
        "done evidence without reasoning": with_evidence(0, reasoning=None),
        "unconfirmed carrying candidate evidence": with_evidence(3, candidate_evidence="ev-01"),
        "evidence layer dropping a skill": {**base_fit, "evidence": evidence[:3]},
        "only two core skills when four skills exist": {**base_fit, "core_skills": core_skills[:2]},
        "core skill that is not a Layer 1 skill": {**base_fit, "core_skills": core_skills[:2] + [
            {"skill_id": "S9", "reason": "x"}]},
        "industry identified but no industry_evidence": {**base_fit, "industry_evidence": None},
        "label disagreeing with the policy aggregation": {**base_fit, "label": "StrongFit"},
    }
    for name, capability_fit in invalid_cases.items():
        try:
            fit_result(capability_fit)
            problems.append(f"expected ValueError for {name}, none raised")
        except Exception:
            pass  # expected


def run() -> None:
    test_location_parser()
    with tempfile.TemporaryDirectory() as tmp:
        test_dedup(Path(tmp))
    test_eligibility()
    test_candidate_profile()
    test_assessment_schema()

    if problems:
        print(f"{len(problems)} PROBLEMS:")
        for p in problems:
            print(f"- {p}")
        raise SystemExit(1)
    print("Phase A smoke test: all checks passed, 0 problems.")


if __name__ == "__main__":
    run()
