"""Stage 8: Capability Fit assessment (capability-fit-v0.3).

Only invoked when Hard Disqualifier's overall_decision is
"ProceedToCapabilityFit". Loads Stage B's instructions from
EVAL_EXECUTION_PROMPT.md and the full capability-fit policy text at runtime,
same pattern as hard_disqualifier.py.

The policy's layers (§3) map to two model calls plus code:

1. Decomposition call -- Layer 1 (hard skills), Layer 2 (the three core
   skills), and the parallel industry variable, as separate output fields. The
   Candidate Profile is deliberately NOT supplied, so no skill can be dropped
   or reworded to suit the CV.
2. Matching call -- a five-state evidence entry for every Layer 1 skill and
   for the industry. The core marking is deliberately NOT supplied, so
   matching isn't pruned by importance.
3. Label -- derived in code by assessment_schema.derive_fit_label (policy §8),
   never chosen by the model.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.assessment_schema import (
    CapabilityFitResult,
    FitCoreSkill,
    FitEvidence,
    FitIndustry,
    FitSkill,
    FitSkillEvidence,
    derive_fit_label,
)
from pipeline.candidate_profile import CandidateProfile
from pipeline.job_schema import Job
from pipeline.llm_common import AssessmentCallFailure, read_doc
from pipeline.model_client import ModelClient

POLICY_VERSION = "capability-fit-v0.3"
POLICY_PATH = Path("docs/llm_eval/CAPABILITY_FIT_POLICY.md")
EXECUTION_PROMPT_PATH = Path("docs/llm_eval/EVAL_EXECUTION_PROMPT.md")

_DECOMPOSITION_INSTRUCTIONS = """\
Apply Layers 1 and 2 and the industry variable of the Capability Fit policy \
above (Sections 4, 5, and 6) to the Job/JD snapshot below. This job has \
already passed Hard Disqualifier -- do not re-run or reconsider that stage.

You are deliberately NOT given the Candidate Profile. Describe only what the \
job requires. Do not assess any candidate.

Return exactly one JSON object with these three keys and no others:

{
  "skills": [
    {
      "skill_id": "S1",            // S1, S2, ... unique within this job
      "skill": string,             // with the functional qualifiers the JD makes material; no industry
      "category": "tool" | "method" | "language" | "credential",
      "jd_signal": "required" | "preferred" | "responsibility",
      "jd_quote": string
    }
  ],
  "core_skills": [
    {"skill_id": "S1", "reason": string}   // exactly 3 (all skills if fewer), most central first
  ],
  "industry": {
    "industry": string | null,             // null only if the JD does not reveal it
    "jd_signal": "required" | "preferred" | "context_only",
    "jd_quote": string | null              // null only when industry is null
  }
}

Produce `skills` first and make it complete: every distinct hard skill the JD \
requires, prefers, or clearly depends on through a responsibility, whether \
minor or not. Then pick `core_skills` from that list; it must not add or \
rename skills. Record industry only in `industry`, never as a skill. Exclude \
soft skills, experience years, degrees, and employment conditions (policy \
§4.1). Do not add a label, score, or recommendation.
"""

_MATCHING_INSTRUCTIONS = """\
Apply Layer 3 of the Capability Fit policy above (Section 7): give every hard \
skill listed in the user message, and the industry, one of the five evidence \
states using only the Candidate Profile above.

You are deliberately NOT told which skills are core. Treat every skill with \
the same care and return exactly one evidence entry per skill_id -- do not \
skip, merge, add, or rename skills.

Return exactly one JSON object with the keys shown and no others:

{
  "evidence": [
    {
      "skill_id": "S1",
      "state": "done" | "participated" | "adjacent" | "unconfirmed" | "not_done",
      "candidate_evidence": string | null,   // evidence id + employer/project + what was done and its result; null only for "unconfirmed"
      "scope": string | null,                // candidate's actual responsibility scope; required for done/participated, else null
      "shifted_dimensions": [ "object" | "customer" | "goal" | "product_context" | "delivery_model" | "tool" | "depth" ],
      "reasoning": string                    // every state: why this state; what is established and what is not (policy §7.3)
    }
  ],
  "industry_evidence": { same fields as an evidence entry, without skill_id },   // only when an industry is given
  "unknowns": [string]                       // missing JD information only
}

A skill the profile does not mention is "unconfirmed", never "not_done"; use \
"not_done" only when the profile explicitly says so, and cite that statement. \
`shifted_dimensions` is non-empty for "adjacent" and empty otherwise. Judge \
each skill against its stated wording and jd_quote; a context difference the \
skill's wording does not name, including industry, is not a shifted \
dimension. If the evidence misses a material part of the skill as worded, the \
state is "adjacent" with "depth"; a minor missing part keeps the state and is \
named in `reasoning`. Background that shares only the setting (same industry \
or product type) is not evidence: the state is "unconfirmed" and the \
background may be mentioned in `reasoning`. `reasoning` explains the one \
assigned state -- never suggest a second state or a stronger verdict. Do not \
add a label, score, or recommendation.
"""

# Anthropic Structured Outputs (output_config.format) schemas -- same rationale
# as hard_disqualifier.py's RESPONSE_SCHEMA. The conditional field rules
# (per-state candidate_evidence/scope/shifted_dimensions), the 3-core
# count, and full-table coverage can't be expressed here; they're enforced by
# assessment_schema's validators.
DECOMPOSITION_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill_id": {"type": "string"},
                    "skill": {"type": "string"},
                    "category": {"type": "string", "enum": ["tool", "method", "language", "credential"]},
                    "jd_signal": {"type": "string", "enum": ["required", "preferred", "responsibility"]},
                    "jd_quote": {"type": "string"},
                },
                "required": ["skill_id", "skill", "category", "jd_signal", "jd_quote"],
                "additionalProperties": False,
            },
        },
        "core_skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"skill_id": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["skill_id", "reason"],
                "additionalProperties": False,
            },
        },
        "industry": {
            "type": "object",
            "properties": {
                "industry": {"type": ["string", "null"]},
                "jd_signal": {"type": "string", "enum": ["required", "preferred", "context_only"]},
                "jd_quote": {"type": ["string", "null"]},
            },
            "required": ["industry", "jd_signal", "jd_quote"],
            "additionalProperties": False,
        },
    },
    "required": ["skills", "core_skills", "industry"],
    "additionalProperties": False,
}

_EVIDENCE_PROPERTIES = {
    "state": {"type": "string",
              "enum": ["done", "participated", "adjacent", "unconfirmed", "not_done"]},
    "candidate_evidence": {"type": ["string", "null"]},
    "scope": {"type": ["string", "null"]},
    "shifted_dimensions": {
        "type": "array",
        "items": {"type": "string",
                  "enum": ["object", "customer", "goal", "product_context",
                           "delivery_model", "tool", "depth"]},
    },
    "reasoning": {"type": "string"},
}
_EVIDENCE_REQUIRED = ["state", "candidate_evidence", "scope", "shifted_dimensions", "reasoning"]


def matching_schema(with_industry: bool) -> dict:
    """The industry_evidence key is present exactly when decomposition
    identified an industry -- avoids a nullable object in the schema."""
    properties = {
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"skill_id": {"type": "string"}, **_EVIDENCE_PROPERTIES},
                "required": ["skill_id", *_EVIDENCE_REQUIRED],
                "additionalProperties": False,
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
    }
    if with_industry:
        properties["industry_evidence"] = {
            "type": "object", "properties": _EVIDENCE_PROPERTIES,
            "required": _EVIDENCE_REQUIRED, "additionalProperties": False,
        }
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


class CapabilityFitEvaluator:
    def __init__(self, model_client: ModelClient, *, max_tokens: int = 3000, temperature: float = 0):
        self.model_client = model_client
        self.max_tokens = max_tokens
        self.temperature = temperature

    def build_decomposition_system_blocks(self) -> list[str]:
        # No Candidate Profile block -- policy §3: Layers 1-2 and industry are CV-blind.
        return [
            read_doc(EXECUTION_PROMPT_PATH),
            read_doc(POLICY_PATH),
            _DECOMPOSITION_INSTRUCTIONS,
        ]

    def build_matching_system_blocks(self, candidate_profile: CandidateProfile) -> list[str]:
        return [
            read_doc(EXECUTION_PROMPT_PATH),
            read_doc(POLICY_PATH),
            "Candidate Profile:\n" + candidate_profile.as_prompt_text(),
            _MATCHING_INSTRUCTIONS,
        ]

    def build_job_snapshot(self, job: Job, raw_description: str) -> str:
        return (
            "Job / JD snapshot:\n"
            f"- job_id: {job.job_id}\n"
            f"- company: {job.company}\n"
            f"- title: {job.title}\n"
            f"- source_url: {job.source_url}\n"
            f"- role_family: {job.role_family}\n"
            f"- description: {job.description}\n"
            f"- responsibilities: {job.responsibilities}\n"
            f"- qualifications_requirements: {job.qualifications_requirements}\n"
            f"- raw_description (full original JD text): {raw_description}\n"
        )

    def build_matching_user_message(self, job: Job, raw_description: str,
                                    skills: list[FitSkill], industry: FitIndustry) -> str:
        # Skills and industry only -- the core marking is withheld (policy §3).
        skill_list = json.dumps([s.model_dump() for s in skills], indent=2, ensure_ascii=False)
        message = (
            self.build_job_snapshot(job, raw_description)
            + "\nHard skills to match (Layer 1, complete list):\n"
            + skill_list + "\n"
        )
        if industry.industry:
            message += f"\nIndustry to match: {industry.industry}\n"
        else:
            message += "\nIndustry: not revealed by the JD -- omit industry_evidence.\n"
        return message

    def _call(self, step: str, system_blocks: list[str], user_message: str,
              schema: dict, expected_keys: set[str]) -> dict | AssessmentCallFailure:
        try:
            result = self.model_client.complete(
                system_blocks=system_blocks, user_message=user_message,
                max_tokens=self.max_tokens, temperature=self.temperature,
                output_schema=schema,
            )
        except Exception as e:
            return AssessmentCallFailure("CapabilityFit", f"{step} call failed: {e}")
        try:
            parsed = json.loads(result.text)
        except json.JSONDecodeError as e:
            return AssessmentCallFailure("CapabilityFit",
                                          f"{step} response is not parseable JSON: {e}", result.text)
        if not isinstance(parsed, dict) or set(parsed.keys()) != expected_keys:
            got = list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__
            return AssessmentCallFailure("CapabilityFit",
                                          f"{step} response keys mismatch, got {got}", result.text)
        return parsed

    def evaluate(self, job: Job, raw_description: str,
                 candidate_profile: CandidateProfile) -> CapabilityFitResult | AssessmentCallFailure:
        decomposition = self._call(
            "decomposition", self.build_decomposition_system_blocks(),
            self.build_job_snapshot(job, raw_description),
            DECOMPOSITION_SCHEMA, {"skills", "core_skills", "industry"},
        )
        if isinstance(decomposition, AssessmentCallFailure):
            return decomposition
        try:
            skills = [FitSkill(**s) for s in decomposition["skills"]]
            industry = FitIndustry(**decomposition["industry"])
        except Exception as e:
            return AssessmentCallFailure("CapabilityFit",
                                          f"decomposition failed schema validation: {e}",
                                          json.dumps(decomposition, ensure_ascii=False))

        with_industry = industry.industry is not None
        matching_keys = {"evidence", "unknowns"} | ({"industry_evidence"} if with_industry else set())
        matching = self._call(
            "matching", self.build_matching_system_blocks(candidate_profile),
            self.build_matching_user_message(job, raw_description, skills, industry),
            matching_schema(with_industry), matching_keys,
        )
        if isinstance(matching, AssessmentCallFailure):
            return matching

        try:
            core_skills = [FitCoreSkill(**c) for c in decomposition["core_skills"]]
            evidence = [FitSkillEvidence(**e) for e in matching["evidence"]]
            industry_evidence = (FitEvidence(**matching["industry_evidence"])
                                 if with_industry else None)
            # CapabilityFitResult's validator enforces the 3-core count and
            # full-table evidence coverage before this result is accepted.
            return CapabilityFitResult(
                policy_version=POLICY_VERSION,
                label=derive_fit_label(core_skills, evidence),
                skills=skills, core_skills=core_skills, industry=industry,
                evidence=evidence, industry_evidence=industry_evidence,
                unknowns=matching["unknowns"],
            )
        except Exception as e:
            return AssessmentCallFailure(
                "CapabilityFit", f"response failed schema validation: {e}",
                json.dumps({**decomposition, **matching}, ensure_ascii=False),
            )
