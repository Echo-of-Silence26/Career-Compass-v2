"""Offline smoke test for the Phase C LLM-calling components.

Zero network/API calls -- every Anthropic client is a stub that returns a
canned response. Confirms prompt assembly (including cache_control
placement) and response-parsing/failure paths before any real spend.

Run: python -m pipeline.validate_phase_c
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.assessment_schema import (
    CapabilityFitResult,
    FitCoreSkill,
    FitSkillEvidence,
    HardDisqualifierResult,
    derive_fit_label,
)
from pipeline.candidate_profile import CandidateProfile
from pipeline.capability_fit import CapabilityFitEvaluator
from pipeline.hard_disqualifier import HardDisqualifierEvaluator
from pipeline.job_extractor import ExtractionFailure, JobExtractor
from pipeline.job_schema import Job
from pipeline.llm_common import AssessmentCallFailure
from pipeline.model_client import AnthropicModelClient
from pipeline.query_catalog import QueryCatalog
from pipeline.source_record import SourceRecord, utcnow_iso

problems: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


class FakeTextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class FakeResponse:
    def __init__(self, text: str):
        self.content = [FakeTextBlock(text)]


class FakeMessages:
    def __init__(self, response_text):
        self._response_text = response_text
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        text = self._response_text(kwargs) if callable(self._response_text) else self._response_text
        return FakeResponse(text)


class FakeClient:
    def __init__(self, response_text):
        self.messages = FakeMessages(response_text)


def _make_source_record() -> SourceRecord:
    return SourceRecord(
        source_record_id="rec-1", source="Indeed", source_job_id="job-123",
        source_url="https://www.indeed.com/viewjob?jk=job-123",
        resolved_url="https://www.indeed.com/viewjob?jk=job-123",
        collection_run_id="run-test", sourcing_config_version="sourcing-config-v0.1",
        source_config_id="indeed-de-v0.1", query_group_id="customer-success-v0.1",
        query_id="cs-customer-success-manager-en-v0.1",
        query_text_or_parameters="Customer Success Manager", captured_at=utcnow_iso(),
        adapter_version="indeed-apify-v0.1", parser_version="indeed-apify-direct-mapping-v0.1",
        capture_method="ApifyActor", raw_title="Customer Success Manager", raw_company="Acme",
        raw_location={"city": "München", "country": "Deutschland"},
        raw_description="Manage enterprise accounts. Requires 3 years experience.",
        raw_publication_date="2026-09-01", raw_job_status=False, raw_work_mode=False,
        raw_payload_reference="inline", content_hash="hash-a", collection_status="Success",
    )


def test_job_extractor_success() -> None:
    valid_json = json.dumps({
        "description": "A role.", "responsibilities": "Manage accounts.",
        "qualifications_requirements": "3 years experience.",
        "description_status": "Full", "work_mode": "Hybrid",
    })
    client = FakeClient(valid_json)
    extractor = JobExtractor(AnthropicModelClient(model="claude-haiku-4-5", client=client),
                              query_catalog=QueryCatalog())
    record = _make_source_record()
    result = extractor.extract(record)
    check(isinstance(result, Job), f"expected a Job, got {type(result)}")
    if isinstance(result, Job):
        check(result.role_family == "CustomerSuccess", f"role_family should be looked up from query_id, got {result.role_family}")
        check(result.matched_search_terms == ["Customer Success Manager"], "matched_search_terms should come from the query catalog")
        check(result.city == "München" and result.country == "Deutschland", "city/country should come from location_parser, not the model")
        check(result.company == "Acme" and result.title == "Customer Success Manager", "company/title should be passthrough from raw fields")


def test_job_extractor_bad_json() -> None:
    client = FakeClient("not json at all")
    extractor = JobExtractor(AnthropicModelClient(model="claude-haiku-4-5", client=client),
                              query_catalog=QueryCatalog())
    result = extractor.extract(_make_source_record())
    check(isinstance(result, ExtractionFailure), f"expected ExtractionFailure, got {type(result)}")


def test_job_extractor_extra_key() -> None:
    bad_json = json.dumps({
        "description": "A role.", "responsibilities": "x", "qualifications_requirements": "y",
        "description_status": "Full", "work_mode": "Hybrid", "extra_field": "nope",
    })
    client = FakeClient(bad_json)
    extractor = JobExtractor(AnthropicModelClient(model="claude-haiku-4-5", client=client),
                              query_catalog=QueryCatalog())
    result = extractor.extract(_make_source_record())
    check(isinstance(result, ExtractionFailure), "an extra key should be treated as a failure, not silently dropped")


def _make_job() -> Job:
    return Job(
        job_id="job_test_1", source="Indeed", source_job_id="job-123",
        source_url="https://www.indeed.com/viewjob?jk=job-123",
        matched_search_terms=["Customer Success Manager"], role_family="CustomerSuccess",
        company="Acme", title="Customer Success Manager", city="München", country="Deutschland",
        work_mode="Hybrid", description="A role.", responsibilities="Manage accounts.",
        qualifications_requirements="3 years experience.", description_status="Full",
        published_at="2026-09-01", content_hash="hash-a", captured_at=utcnow_iso(), updated_at=utcnow_iso(),
    )


def test_hard_disqualifier_success_and_caching() -> None:
    valid_json = json.dumps({
        "rules": [
            {"rule_id": "3.2", "rule_name": "compensation", "state": "Unknown",
             "evidence_quote": None, "candidate_evidence": None, "reason": "Not disclosed."},
        ],
        "overall_decision": "ProceedToCapabilityFit",
    })
    client = FakeClient(valid_json)
    evaluator = HardDisqualifierEvaluator(AnthropicModelClient(model="claude-sonnet-5", client=client))
    profile = CandidateProfile.load()
    result = evaluator.evaluate(_make_job(), "full raw JD text here", profile)
    check(isinstance(result, HardDisqualifierResult), f"expected HardDisqualifierResult, got {result}")

    call_kwargs = client.messages.last_call_kwargs
    check(call_kwargs is not None, "client.messages.create should have been called")
    system_blocks = call_kwargs["system"]
    check(system_blocks[-1].get("cache_control") == {"type": "ephemeral"},
          "the last system block should carry cache_control for prompt caching")
    check(all("cache_control" not in b for b in system_blocks[:-1]),
          "only the last system block should carry cache_control")


def test_hard_disqualifier_bad_response() -> None:
    client = FakeClient(json.dumps({"unexpected": "shape"}))
    evaluator = HardDisqualifierEvaluator(AnthropicModelClient(model="claude-sonnet-5", client=client))
    profile = CandidateProfile.load()
    result = evaluator.evaluate(_make_job(), "raw JD text", profile)
    check(isinstance(result, AssessmentCallFailure), f"expected AssessmentCallFailure, got {type(result)}")


_FIT_DECOMPOSITION = {
    "skills": [
        {"skill_id": "S1", "skill": "B2B account management", "category": "method",
         "jd_signal": "required", "jd_quote": "Manage enterprise accounts."},
        {"skill_id": "S2", "skill": "Enterprise SaaS end-user onboarding and adoption",
         "category": "method", "jd_signal": "responsibility", "jd_quote": "Drive adoption."},
        {"skill_id": "S3", "skill": "Customer health-score monitoring", "category": "method",
         "jd_signal": "required", "jd_quote": "Track account health."},
        {"skill_id": "S4", "skill": "Salesforce", "category": "tool",
         "jd_signal": "preferred", "jd_quote": "Salesforce is a plus."},
    ],
    "core_skills": [
        {"skill_id": "S1", "reason": "Central function."},
        {"skill_id": "S2", "reason": "Primary responsibility."},
        {"skill_id": "S3", "reason": "Retention depends on it."},
    ],
    "industry": {"industry": "HR software (B2B SaaS)", "jd_signal": "preferred",
                 "jd_quote": "Experience in HR tech is a plus."},
}

_FIT_MATCHING = {
    "evidence": [
        {"skill_id": "S1", "state": "done", "candidate_evidence": "ev-01: pharma B2B accounts",
         "scope": "Owned two named accounts end-to-end.", "shifted_dimensions": [],
         "reasoning": "Owned renewal-critical B2B accounts; covers the skill as worded."},
        {"skill_id": "S2", "state": "adjacent", "candidate_evidence": "ev-01: programme launches",
         "scope": None, "shifted_dimensions": ["object", "goal"],
         "reasoning": "Structured B2B onboarding transfers; patients, not employees."},
        {"skill_id": "S3", "state": "participated", "candidate_evidence": "ev-01: monitored KPIs",
         "scope": "Monitored programme KPIs; no health-score model ownership.",
         "shifted_dimensions": [], "reasoning": "Tracked KPIs someone else defined."},
        {"skill_id": "S4", "state": "unconfirmed", "candidate_evidence": None, "scope": None,
         "shifted_dimensions": [], "reasoning": "No Salesforce use in the CV. Have you used it hands-on?"},
    ],
    "industry_evidence": {"state": "adjacent", "candidate_evidence": "ev-01: B2B SaaS health app",
                          "scope": None, "shifted_dimensions": ["product_context"],
                          "reasoning": "B2B SaaS transfers; healthcare, not HR tech."},
    "unknowns": [],
}


class RecordingFitClient:
    """Answers the decomposition and matching calls by requested schema, and
    records every call's kwargs so prompt isolation can be asserted."""

    def __init__(self, decomposition: dict, matching: dict):
        self.calls: list[dict] = []
        self.messages = self
        self._decomposition = decomposition
        self._matching = matching

    def create(self, **kwargs):
        self.calls.append(kwargs)
        keys = set(kwargs["output_config"]["format"]["schema"]["properties"])
        return FakeResponse(json.dumps(self._decomposition if "skills" in keys else self._matching))


def _run_fit(decomposition: dict, matching: dict):
    client = RecordingFitClient(decomposition, matching)
    evaluator = CapabilityFitEvaluator(AnthropicModelClient(model="claude-sonnet-5", client=client))
    return evaluator.evaluate(_make_job(), "raw JD text", CandidateProfile.load()), client


def test_capability_fit_success_and_isolation() -> None:
    result, client = _run_fit(_FIT_DECOMPOSITION, _FIT_MATCHING)
    check(isinstance(result, CapabilityFitResult), f"expected CapabilityFitResult, got {result}")
    if isinstance(result, CapabilityFitResult):
        check(result.label == "PlausibleFit",
              f"core done + adjacent + participated should derive PlausibleFit, got {result.label}")
        check(len(result.evidence) == 4, "every skill, core or not, should carry an evidence entry")
        check(result.industry_evidence is not None and result.industry_evidence.state == "adjacent",
              "industry should be matched in parallel")

    check(len(client.calls) == 2, f"expected 2 model calls (decomposition, matching), got {len(client.calls)}")
    if len(client.calls) == 2:
        decomposition_call, matching_call = client.calls
        decomposition_system = "".join(b["text"] for b in decomposition_call["system"])
        check("Candidate Profile:" not in decomposition_system
              and "evidence_items" not in decomposition_system,
              "decomposition call must be CV-blind (policy §3)")
        matching_user = matching_call["messages"][0]["content"]
        check("core_skills" not in matching_user and "Central function." not in matching_user,
              "matching call must not see the core marking (policy §3)")
        check("Enterprise SaaS end-user onboarding" in matching_user and "Salesforce" in matching_user,
              "matching call must receive the full Layer 1 skill list, core and non-core")
        check("HR software (B2B SaaS)" in matching_user, "matching call must receive the industry")
        check("industry_evidence" in matching_call["output_config"]["format"]["schema"]["properties"],
              "matching schema should request industry_evidence when an industry was identified")
        for call in client.calls:
            check(call["system"][-1].get("cache_control") == {"type": "ephemeral"},
                  "both Fit calls should cache their static system context")


def test_capability_fit_without_industry() -> None:
    decomposition = {**_FIT_DECOMPOSITION,
                     "industry": {"industry": None, "jd_signal": "context_only", "jd_quote": None}}
    matching = {k: v for k, v in _FIT_MATCHING.items() if k != "industry_evidence"}
    result, client = _run_fit(decomposition, matching)
    check(isinstance(result, CapabilityFitResult), f"a JD without an industry should still evaluate, got {result}")
    if len(client.calls) == 2:
        check("industry_evidence" not in client.calls[1]["output_config"]["format"]["schema"]["properties"],
              "matching schema should omit industry_evidence when no industry was identified")


def test_capability_fit_matching_drops_a_skill() -> None:
    partial = {**_FIT_MATCHING, "evidence": _FIT_MATCHING["evidence"][:3]}  # non-core S4 skipped
    result, _ = _run_fit(_FIT_DECOMPOSITION, partial)
    check(isinstance(result, AssessmentCallFailure)
          and "cover every Layer 1 skill" in result.reason,
          f"matching that skips a skill should fail the full-table check, got {result}")


def test_capability_fit_wrong_core_count() -> None:
    two_core = {**_FIT_DECOMPOSITION, "core_skills": _FIT_DECOMPOSITION["core_skills"][:2]}
    result, _ = _run_fit(two_core, _FIT_MATCHING)
    check(isinstance(result, AssessmentCallFailure) and "core_skills must name 3" in result.reason,
          f"two core skills out of four should fail the top-3 rule, got {result}")


def test_capability_fit_silence_as_not_done() -> None:
    bad = {**_FIT_MATCHING, "evidence": _FIT_MATCHING["evidence"][:3] + [
        {**_FIT_MATCHING["evidence"][3], "state": "not_done"}]}  # no citation
    result, _ = _run_fit(_FIT_DECOMPOSITION, bad)
    check(isinstance(result, AssessmentCallFailure) and "requires candidate_evidence" in result.reason,
          f"not_done without an explicit profile citation should fail, got {result}")


def test_fit_label_aggregation() -> None:
    def ev(skill_id: str, state: str) -> FitSkillEvidence:
        return FitSkillEvidence(
            skill_id=skill_id, state=state,
            candidate_evidence=None if state == "unconfirmed" else "ev",
            scope="scope" if state in ("done", "participated") else None,
            shifted_dimensions=["object"] if state == "adjacent" else [],
            reasoning="r")

    def label(core_states: list[str], non_core_state: str = "not_done") -> str:
        core = [FitCoreSkill(skill_id=f"C{i}", reason="r") for i in range(len(core_states))]
        evidence = [ev(f"C{i}", st) for i, st in enumerate(core_states)] + [ev("N", non_core_state)]
        return derive_fit_label(core, evidence)

    cases = [
        ([], "Unclear", "no hard skill"),
        (["done", "done", "done"], "StrongFit", "all core done; non-core not_done ignored"),
        (["done", "participated", "adjacent"], "PlausibleFit", "one core done, rest partial"),
        (["participated", "adjacent", "adjacent"], "WeakFit", "no core done"),
        (["done", "done", "not_done"], "WeakFit", "confirmed core gap"),
        (["done", "done", "unconfirmed"], "Unclear", "confirmation could change the label"),
        (["not_done", "unconfirmed", "done"], "WeakFit", "confirmed gap decides despite unconfirmed"),
    ]
    for core_states, expected, why in cases:
        got = label(core_states)
        check(got == expected, f"aggregation ({why}): expected {expected}, got {got}")


def run() -> None:
    test_job_extractor_success()
    test_job_extractor_bad_json()
    test_job_extractor_extra_key()
    test_hard_disqualifier_success_and_caching()
    test_hard_disqualifier_bad_response()
    test_capability_fit_success_and_isolation()
    test_capability_fit_without_industry()
    test_capability_fit_matching_drops_a_skill()
    test_capability_fit_wrong_core_count()
    test_capability_fit_silence_as_not_done()
    test_fit_label_aggregation()

    if problems:
        print(f"{len(problems)} PROBLEMS:")
        for p in problems:
            print(f"- {p}")
        raise SystemExit(1)
    print("Phase C smoke test: all checks passed, 0 problems, 0 live API calls made.")


if __name__ == "__main__":
    run()
