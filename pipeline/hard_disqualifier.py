"""Stage 6: Hard Disqualifier assessment.

Loads Stage A's instructions from EVAL_EXECUTION_PROMPT.md and the full
frozen hard-disqualifier-v0.2 policy text at runtime (not
duplicated into code -- the doc stays the single source of truth), supplies
the Job/JD snapshot + Candidate Profile, calls the model, and validates the
response against assessment_schema.HardDisqualifierResult. An invalid or
failed call returns an AssessmentCallFailure -- never a silently-repaired
result.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.assessment_schema import HardDisqualifierResult
from pipeline.candidate_profile import CandidateProfile
from pipeline.job_schema import Job
from pipeline.llm_common import AssessmentCallFailure, read_doc
from pipeline.model_client import ModelClient

POLICY_VERSION = "hard-disqualifier-v0.2"
POLICY_PATH = Path("docs/llm_eval/HARD_DISQUALIFIER_POLICY.md")
EXECUTION_PROMPT_PATH = Path("docs/llm_eval/EVAL_EXECUTION_PROMPT.md")

_OUTPUT_INSTRUCTIONS = """\
Evaluate every rule in the policy above against the Job/JD snapshot and \
Candidate Profile below (Stage A only -- do not run Capability Fit here).

Return exactly one JSON object with these two keys and no others, no \
markdown fencing, no commentary before or after it:

{
  "rules": [
    {
      "rule_id": string,          // e.g. "3.1(b)", exactly as numbered in the policy
      "rule_name": string,        // short slug, e.g. "senior_years"
      "state": "Pass" | "Fail" | "Unknown" | "Flag",
      "evidence_quote": string | null,
      "candidate_evidence": string | null,
      "reason": string
    }
  ],
  "overall_decision": "Exclude" | "ProceedToCapabilityFit"
}

Evaluate one entry per policy rule (3.1(a), 3.1(b), 3.1(c), 3.2, 3.3, 3.4, \
3.5, 3.6). `evidence_quote` is required (non-null) for every Fail, Unknown, \
or Flag; it may be null only for Pass. Any Fail -> overall_decision \
"Exclude". No Fail -> overall_decision "ProceedToCapabilityFit". Do not add \
extra keys or commentary outside the JSON object.
"""

# Anthropic Structured Outputs (output_config.format) schema for this stage's
# response -- mirrors the shape in _OUTPUT_INSTRUCTIONS above and the keys
# checked in parse_response(). Added after claude-sonnet-5 was observed
# wrapping this stage's JSON in a ```json fence in a live run (2026-09-05),
# same failure mode already fixed for extraction in pipeline/job_extractor.py.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string"},
                    "rule_name": {"type": "string"},
                    "state": {"type": "string", "enum": ["Pass", "Fail", "Unknown", "Flag"]},
                    "evidence_quote": {"type": ["string", "null"]},
                    "candidate_evidence": {"type": ["string", "null"]},
                    "reason": {"type": "string"},
                },
                "required": ["rule_id", "rule_name", "state", "evidence_quote",
                             "candidate_evidence", "reason"],
                "additionalProperties": False,
            },
        },
        "overall_decision": {"type": "string", "enum": ["Exclude", "ProceedToCapabilityFit"]},
    },
    "required": ["rules", "overall_decision"],
    "additionalProperties": False,
}


class HardDisqualifierEvaluator:
    def __init__(self, model_client: ModelClient, *, max_tokens: int = 3000, temperature: float = 0):
        self.model_client = model_client
        self.max_tokens = max_tokens
        self.temperature = temperature

    def build_system_blocks(self, candidate_profile: CandidateProfile) -> list[str]:
        return [
            read_doc(EXECUTION_PROMPT_PATH),
            read_doc(POLICY_PATH),
            "Candidate Profile:\n" + candidate_profile.as_prompt_text(),
            _OUTPUT_INSTRUCTIONS,
        ]

    def build_user_message(self, job: Job, raw_description: str) -> str:
        return (
            "Job / JD snapshot:\n"
            f"- job_id: {job.job_id}\n"
            f"- company: {job.company}\n"
            f"- title: {job.title}\n"
            f"- source_url: {job.source_url}\n"
            f"- role_family: {job.role_family}\n"
            f"- city: {job.city}\n"
            f"- country: {job.country}\n"
            f"- work_mode: {job.work_mode}\n"
            f"- description: {job.description}\n"
            f"- responsibilities: {job.responsibilities}\n"
            f"- qualifications_requirements: {job.qualifications_requirements}\n"
            f"- raw_description (full original JD text): {raw_description}\n"
        )

    def parse_response(self, response_text: str) -> dict | AssessmentCallFailure:
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as e:
            return AssessmentCallFailure("HardDisqualifier",
                                          f"response is not parseable JSON: {e}", response_text)
        if not isinstance(parsed, dict) or set(parsed.keys()) != {"rules", "overall_decision"}:
            got = list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__
            return AssessmentCallFailure("HardDisqualifier",
                                          f"response keys mismatch, got {got}", response_text)
        return parsed

    def evaluate(self, job: Job, raw_description: str,
                 candidate_profile: CandidateProfile) -> HardDisqualifierResult | AssessmentCallFailure:
        system_blocks = self.build_system_blocks(candidate_profile)
        user_message = self.build_user_message(job, raw_description)

        try:
            result = self.model_client.complete(
                system_blocks=system_blocks, user_message=user_message,
                max_tokens=self.max_tokens, temperature=self.temperature,
                output_schema=RESPONSE_SCHEMA,
            )
        except Exception as e:
            return AssessmentCallFailure("HardDisqualifier", f"API call failed: {e}")

        parsed = self.parse_response(result.text)
        if isinstance(parsed, AssessmentCallFailure):
            return parsed

        try:
            return HardDisqualifierResult(
                policy_version=POLICY_VERSION,
                rules=parsed["rules"],
                overall_decision=parsed["overall_decision"],
            )
        except Exception as e:
            return AssessmentCallFailure("HardDisqualifier",
                                          f"response failed schema validation: {e}", result.text)
