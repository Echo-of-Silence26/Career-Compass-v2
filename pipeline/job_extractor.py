"""Stage 4: LLM Job extraction.

Loads the exact prompt text from docs/data_pipeline/JOB_EXTRACTION_PROMPT_MVP.md
§5 verbatim (not re-derived), fills it with one RawJobRecord's fields, calls
the configured model, validates the 5-key JSON response per §6/§7, and merges
it with the deterministic passthrough fields (§2) to assemble a full `Job`.

Per ADR-015: one dedicated LLM call per record, no retry/repair on failure --
an invalid response becomes an ExtractionFailure the caller routes to human
review, never a silently-repaired Job.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from string import Template
from typing import Any

# Some models wrap the requested JSON in a markdown code fence despite the
# prompt's explicit "no markdown fencing" instruction. This strips only that
# envelope (leading ```/```json line and trailing ``` line) before parsing --
# it never touches the JSON content itself, so it is not a content repair
# per ADR-015: a response that isn't valid JSON even after unwrapping still
# fails parsing exactly as before.
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*)\n```\s*$", re.DOTALL)

from pipeline.job_schema import Job
from pipeline.location_parser import parse_location
from pipeline.model_client import ModelClient
from pipeline.query_catalog import QueryCatalog
from pipeline.source_record import SourceRecord, utcnow_iso

PROMPT_VERSION = "job-extraction-v0.1"

# Verbatim from JOB_EXTRACTION_PROMPT_MVP.md §5. Do not edit the instructions
# without bumping PROMPT_VERSION and updating that doc first -- it is the
# frozen source of truth, this is its executable form.
_PROMPT_TEMPLATE = Template("""\
You are extracting structured facts from one captured job posting. Use only
the JD text and source signals supplied below — never outside knowledge,
never a live page fetch, never a guess about what a posting "probably" says.

Given:
- source: $source
- raw_title: $raw_title
- raw_company: $raw_company
- raw_location: $raw_location        # context only; do not re-emit city/country from this
- raw_publication_date: $raw_publication_date
- raw_job_status: $raw_job_status    # e.g. Indeed's `expired` boolean, when available
- raw_work_mode: $raw_work_mode      # e.g. Indeed's `isRemote` boolean, when available
- raw_description: $raw_description  # primary evidence — the full captured JD text

Produce exactly these five fields, and no others:

1. description — the general role, team, company, and position overview.
   Exclude specific responsibilities and exclude requirements/qualifications.

2. responsibilities — the responsibilities, activities, and expected
   deliverables stated for this role. Preserve source wording; do not
   summarize away specific verbs, tools, or deliverables. A statement
   belongs here based on what it says, not on which heading it sits under
   in the source text.

3. qualifications_requirements — the experience, skills, languages,
   education, and other stated requirements, including preferred/"nice to
   have" qualifications. A statement belongs here based on what it says,
   not on which heading it sits under in the source text.

4. description_status — one of:
   - "Full" when both responsibilities-type and requirements-type content
     are clearly present in raw_description;
   - "Partial" when raw_description has content but looks cut short,
     preview-only, or is clearly missing one of the two categories above;
   - "Missing" when raw_description is empty or near-empty after
     whitespace trimming.
   This is a lightweight extraction-time signal, not a rigorous
   completeness judgment.

5. work_mode — one of "Remote", "Hybrid", "OnSite", "Unknown". Use
   raw_work_mode as a hint only — it is boolean-only where present and
   cannot by itself distinguish Hybrid from OnSite. The JD text in
   raw_description is the primary evidence (e.g. explicit "hybrid", "N
   days per week in the office", "fully remote", "on-site" language). If
   the text gives no work-location signal at all and raw_work_mode is
   absent or uninformative, return "Unknown" — never guess.

If a field's content is not present in raw_description, return null for a
text field. Do not invent, merge in, or "clean up" facts not stated in the
text. Do not reason about candidate fit, disqualification, or seniority
match — extraction states only what the posting itself says.

Return exactly one JSON object with these five keys and no others, no
markdown fencing, no commentary before or after it:

{
  "description": string | null,
  "responsibilities": string | null,
  "qualifications_requirements": string | null,
  "description_status": "Full" | "Partial" | "Missing",
  "work_mode": "Remote" | "Hybrid" | "OnSite" | "Unknown"
}""")

REQUIRED_KEYS = {
    "description", "responsibilities", "qualifications_requirements",
    "description_status", "work_mode",
}
ALLOWED_DESCRIPTION_STATUS = {"Full", "Partial", "Missing"}
ALLOWED_WORK_MODE = {"Remote", "Hybrid", "OnSite", "Unknown"}

# Anthropic Structured Outputs (output_config.format) schema for this stage's
# response -- mirrors REQUIRED_KEYS/ALLOWED_DESCRIPTION_STATUS/ALLOWED_WORK_MODE
# above. Passed to ModelClient.complete(output_schema=...) so the response is
# guaranteed (decode-time, not prompt-level) to be exactly this shape -- no
# markdown fencing, no missing/extra keys, no out-of-enum values. Verified
# live against claude-haiku-4-5 and claude-sonnet-5 (2026-09-05).
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": ["string", "null"]},
        "responsibilities": {"type": ["string", "null"]},
        "qualifications_requirements": {"type": ["string", "null"]},
        "description_status": {"type": "string", "enum": sorted(ALLOWED_DESCRIPTION_STATUS)},
        "work_mode": {"type": "string", "enum": sorted(ALLOWED_WORK_MODE)},
    },
    "required": sorted(REQUIRED_KEYS),
    "additionalProperties": False,
}


@dataclass
class ExtractionFailure:
    reason: str
    raw_response_text: str | None = None


class JobExtractor:
    def __init__(self, model_client: ModelClient, *, max_tokens: int = 2000,
                 temperature: float = 0, query_catalog: QueryCatalog | None = None):
        self.model_client = model_client
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._query_catalog = query_catalog

    def _get_query_catalog(self) -> QueryCatalog:
        if self._query_catalog is None:
            self._query_catalog = QueryCatalog()
        return self._query_catalog

    def build_prompt(self, record: SourceRecord) -> str:
        return _PROMPT_TEMPLATE.substitute(
            source=record.source,
            raw_title=record.raw_title,
            raw_company=record.raw_company,
            raw_location=record.raw_location,
            raw_publication_date=record.raw_publication_date,
            raw_job_status=record.raw_job_status,
            raw_work_mode=record.raw_work_mode,
            raw_description=record.raw_description,
        )

    def parse_response(self, response_text: str) -> dict[str, Any] | ExtractionFailure:
        """Structural validation only, per §7: parseable JSON, exactly the
        five required keys, enum values within the allowed set. No repair."""
        fence_match = _CODE_FENCE_RE.match(response_text.strip())
        unwrapped = fence_match.group(1) if fence_match else response_text
        try:
            parsed = json.loads(unwrapped)
        except json.JSONDecodeError as e:
            return ExtractionFailure(reason=f"response is not parseable JSON: {e}",
                                      raw_response_text=response_text)

        if not isinstance(parsed, dict):
            return ExtractionFailure(reason="response JSON is not an object",
                                      raw_response_text=response_text)

        keys = set(parsed.keys())
        if keys != REQUIRED_KEYS:
            missing = REQUIRED_KEYS - keys
            extra = keys - REQUIRED_KEYS
            return ExtractionFailure(
                reason=f"response keys mismatch (missing={sorted(missing)}, extra={sorted(extra)})",
                raw_response_text=response_text,
            )

        if parsed["description_status"] not in ALLOWED_DESCRIPTION_STATUS:
            return ExtractionFailure(
                reason=f"invalid description_status: {parsed['description_status']!r}",
                raw_response_text=response_text,
            )
        if parsed["work_mode"] not in ALLOWED_WORK_MODE:
            return ExtractionFailure(
                reason=f"invalid work_mode: {parsed['work_mode']!r}",
                raw_response_text=response_text,
            )
        for text_field in ("description", "responsibilities", "qualifications_requirements"):
            value = parsed[text_field]
            if value is not None and not isinstance(value, str):
                return ExtractionFailure(
                    reason=f"'{text_field}' must be string or null, got {type(value).__name__}",
                    raw_response_text=response_text,
                )

        return parsed

    def extract(self, record: SourceRecord) -> Job | ExtractionFailure:
        prompt = self.build_prompt(record)
        result = self.model_client.complete(
            system_blocks=[], user_message=prompt,
            max_tokens=self.max_tokens, temperature=self.temperature,
            output_schema=RESPONSE_SCHEMA,
        )
        response_text = result.text

        parsed = self.parse_response(response_text)
        if isinstance(parsed, ExtractionFailure):
            return parsed

        query = self._get_query_catalog().get(record.query_id)
        city, country = parse_location(record.source, record.raw_location)
        now = utcnow_iso()

        return Job(
            job_id=f"job_{uuid.uuid4().hex}",
            source=record.source,
            source_job_id=record.source_job_id,
            source_url=record.source_url,
            matched_search_terms=[query.term],
            role_family=query.role_family,
            company=record.raw_company,
            title=record.raw_title,
            city=city,
            country=country,
            work_mode=parsed["work_mode"],
            description=parsed["description"],
            responsibilities=parsed["responsibilities"],
            qualifications_requirements=parsed["qualifications_requirements"],
            description_status=parsed["description_status"],
            published_at=record.raw_publication_date,
            content_hash=record.content_hash,
            captured_at=record.captured_at,
            updated_at=now,
        )
