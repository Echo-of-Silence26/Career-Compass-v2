"""Executable contract for the evaluation result.

Mirrors docs/llm_eval/EVAL_RESULT_SCHEMA_MVP.md §2 (canonical
shape) and §4 (cross-field validation rules) exactly. Used to validate every
Hard-Disqualifier/Capability-Fit model response before it is persisted -- an
invalid response becomes a `Failed` record (see pipeline/hard_disqualifier.py
and pipeline/capability_fit.py), never a silently-repaired one.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "eval-result-v0.2"


class HardDisqualifierRule(BaseModel):
    rule_id: str
    rule_name: str
    state: Literal["Pass", "Fail", "Unknown", "Flag"]
    evidence_quote: str | None = None
    candidate_evidence: str | None = None
    reason: str


class HardDisqualifierResult(BaseModel):
    policy_version: str | None = None
    rules: list[HardDisqualifierRule] = Field(default_factory=list)
    overall_decision: Literal["Exclude", "ProceedToCapabilityFit"] | None = None


FitLabel = Literal["StrongFit", "PlausibleFit", "WeakFit", "Unclear"]
EvidenceState = Literal["done", "participated", "adjacent", "unconfirmed", "not_done"]
ShiftedDimension = Literal["object", "customer", "goal", "product_context",
                           "delivery_model", "tool", "depth"]
CORE_SKILL_COUNT = 3  # CAPABILITY_FIT_POLICY.md §5


class FitSkill(BaseModel):
    """Layer 1 -- policy §4 (CV-blind)."""
    skill_id: str
    skill: str
    category: Literal["tool", "method", "language", "credential"]
    jd_signal: Literal["required", "preferred", "responsibility"]
    jd_quote: str


class FitCoreSkill(BaseModel):
    """Layer 2 -- policy §5 (CV-blind): one of the three most central skills."""
    skill_id: str
    reason: str


class FitIndustry(BaseModel):
    """Parallel industry variable -- policy §6 (CV-blind)."""
    industry: str | None = None
    jd_signal: Literal["required", "preferred", "context_only"]
    jd_quote: str | None = None

    @model_validator(mode="after")
    def _quote_rule(self):
        if self.industry and not self.jd_quote:
            raise ValueError("an identified industry requires a jd_quote")
        if not self.industry and self.jd_quote:
            raise ValueError("a null industry must have a null jd_quote")
        return self


class FitEvidence(BaseModel):
    """Layer 3 evidence state -- policy §7. Used for the industry directly and,
    via FitSkillEvidence, for each skill."""
    state: EvidenceState
    candidate_evidence: str | None = None
    scope: str | None = None
    shifted_dimensions: list[ShiftedDimension] = Field(default_factory=list)
    reasoning: str | None = None

    @model_validator(mode="after")
    def _state_field_rules(self):
        # Policy §7.3 field rules.
        subject = getattr(self, "skill_id", "industry")
        if not self.reasoning:
            # Every state: it is the Assessment column of the skill-map table (§9.1).
            raise ValueError(f"{subject}: '{self.state}' requires reasoning")
        if self.state == "unconfirmed":
            if self.candidate_evidence:
                raise ValueError(f"{subject}: 'unconfirmed' must have null candidate_evidence")
        elif not self.candidate_evidence:
            # not_done included: it must cite the explicit profile statement,
            # so silence can't be recorded as a confirmed gap.
            raise ValueError(f"{subject}: '{self.state}' requires candidate_evidence")
        if self.state in ("done", "participated"):
            if not self.scope:
                raise ValueError(f"{subject}: '{self.state}' requires the responsibility scope")
        elif self.scope:
            raise ValueError(f"{subject}: only 'done'/'participated' may record a scope")
        if self.state == "adjacent":
            if not self.shifted_dimensions:
                raise ValueError(f"{subject}: 'adjacent' requires shifted_dimensions")
        elif self.shifted_dimensions:
            raise ValueError(f"{subject}: only 'adjacent' may list shifted_dimensions")
        return self


class FitSkillEvidence(FitEvidence):
    skill_id: str


def derive_fit_label(core_skills: list[FitCoreSkill], evidence: list[FitSkillEvidence]) -> FitLabel:
    """Policy §8 aggregation over the core skills' states only."""
    core_ids = {c.skill_id for c in core_skills}
    states = [e.state for e in evidence if e.skill_id in core_ids]
    if not states:
        return "Unclear"
    if "not_done" in states:
        return "WeakFit"
    if "unconfirmed" in states:
        return "Unclear"
    if all(s == "done" for s in states):
        return "StrongFit"
    if "done" not in states:
        return "WeakFit"
    return "PlausibleFit"


class CapabilityFitResult(BaseModel):
    policy_version: str | None = None
    label: FitLabel | None = None
    skills: list[FitSkill] = Field(default_factory=list)
    core_skills: list[FitCoreSkill] = Field(default_factory=list)
    industry: FitIndustry | None = None
    evidence: list[FitSkillEvidence] = Field(default_factory=list)
    industry_evidence: FitEvidence | None = None
    unknowns: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _layer_rules(self):
        if self.label is None:
            if (self.skills or self.core_skills or self.evidence
                    or self.industry is not None or self.industry_evidence is not None):
                raise ValueError("a Fit result without a label must not carry skill layers")
            return self

        skill_ids = [s.skill_id for s in self.skills]
        if len(set(skill_ids)) != len(skill_ids):
            raise ValueError(f"duplicate skill_id in Layer 1: {skill_ids}")

        core_ids = [c.skill_id for c in self.core_skills]
        expected_core = min(CORE_SKILL_COUNT, len(skill_ids))
        if len(core_ids) != expected_core or len(set(core_ids)) != len(core_ids):
            raise ValueError(f"core_skills must name {expected_core} distinct skills, got {core_ids}")
        if not set(core_ids) <= set(skill_ids):
            raise ValueError(f"core_skills {core_ids} must be Layer 1 skills {skill_ids}")

        # Policy §3: Layer 3 matches the full Layer 1 list -- no skill
        # dropped, added, or matched twice.
        evidence_ids = [e.skill_id for e in self.evidence]
        if sorted(evidence_ids) != sorted(skill_ids):
            raise ValueError(
                f"evidence must cover every Layer 1 skill exactly once; "
                f"skills={skill_ids}, evidence={evidence_ids}"
            )

        if self.industry is None:
            raise ValueError("a labelled Fit result requires the industry field")
        if (self.industry.industry is None) != (self.industry_evidence is None):
            raise ValueError("industry_evidence is required exactly when an industry is identified")

        expected = derive_fit_label(self.core_skills, self.evidence)
        if self.label != expected:
            raise ValueError(f"label {self.label} disagrees with policy §8 aggregation ({expected})")
        return self

    def core_ids(self) -> set[str]:
        return {c.skill_id for c in self.core_skills}


class EvaluationResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    evaluation_id: str
    job_id: str
    run_id: str

    company: str
    title: str
    source_url: str
    job_content_hash: str
    candidate_profile_version: str

    input_status: Literal["Eligible", "Blocked"]
    blocking_reasons: list[str] = Field(default_factory=list)

    hard_disqualifier: HardDisqualifierResult
    capability_fit: CapabilityFitResult

    fit_skip_reason: Literal["HardDisqualifierFail"] | None = None

    evaluation_status: Literal["Completed", "Blocked", "Failed"]
    failure_stage: Literal["HardDisqualifier", "CapabilityFit"] | None = None
    failure_reason: str | None = None

    prompt_version: str
    model_identifier: str
    model_config_version: str
    output_schema_version: str = SCHEMA_VERSION
    evaluated_at: str

    @model_validator(mode="after")
    def _cross_field_rules(self):
        hd = self.hard_disqualifier
        fit = self.capability_fit
        any_fail = any(r.state == "Fail" for r in hd.rules)

        if self.input_status == "Blocked":
            if self.evaluation_status != "Blocked":
                raise ValueError("Blocked input_status requires evaluation_status Blocked")
            if not self.blocking_reasons:
                raise ValueError("Blocked input_status requires non-empty blocking_reasons")
            if hd.rules or hd.overall_decision is not None:
                raise ValueError("Blocked input_status requires empty HD rules/decision")
            if fit.label is not None:
                raise ValueError("Blocked input_status requires a null Fit label")
            if self.fit_skip_reason is not None:
                raise ValueError("Blocked input_status requires a null fit_skip_reason")
            if self.failure_stage is not None or self.failure_reason is not None:
                raise ValueError("Blocked input_status requires null failure fields")

        if self.input_status == "Eligible" and self.blocking_reasons:
            raise ValueError("Eligible input_status requires empty blocking_reasons")

        if any_fail:
            if hd.overall_decision != "Exclude":
                raise ValueError("Any HD Fail requires overall_decision Exclude")
            if fit.policy_version is not None or fit.label is not None:
                raise ValueError("Any HD Fail requires a null Capability-Fit policy/label")
            if self.fit_skip_reason != "HardDisqualifierFail":
                raise ValueError("Any HD Fail requires fit_skip_reason HardDisqualifierFail")

        if hd.rules and not any_fail and hd.overall_decision != "ProceedToCapabilityFit":
            raise ValueError("No HD Fail requires overall_decision ProceedToCapabilityFit")

        if (hd.overall_decision == "ProceedToCapabilityFit"
                and self.evaluation_status == "Completed"):
            if fit.policy_version is None or fit.label is None:
                raise ValueError(
                    "A completed ProceedToCapabilityFit result requires a Fit "
                    "policy version and exactly one Fit label"
                )
            if self.fit_skip_reason is not None:
                raise ValueError("A completed Fit result requires a null fit_skip_reason")

        if self.evaluation_status == "Failed":
            if self.failure_stage is None or not self.failure_reason:
                raise ValueError("Failed evaluation_status requires failure_stage and failure_reason")

        return self
