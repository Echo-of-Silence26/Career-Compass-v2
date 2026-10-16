# MVP Workflow Stage and Contract Map

Status: Active implementation map v0.1  
Created: 2026-08-29  
Runtime owner: [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) v0.9

## 1. Purpose

This document maps the accepted first-runnable-MVP workflow to the technical
component, implementation responsibility, business rule, and data contract
needed to write each stage. It is a navigation and dependency map, not a
replacement for the owning specifications.

Accepted workflow:

```text
manual run
-> Indeed discovery
-> capture + persist RawJobRecord
-> pre-extraction deduplication
-> LLM Job extraction
-> minimal input guard
-> Hard Disqualifier LLM
-> Capability Fit LLM when no confirmed Fail
-> JSONL persistence and reconciliation
-> Excel human-review export
```

## 2. Workflow Map

| # | Stage | Operations performed | Technical component | MVP implementation approach | Input -> output | Owning technical specification | Business rules / configuration | Data contract | Contract readiness |
|---:|---|---|---|---|---|---|---|---|---|
| 0 | Manual run initiation | Accept one frozen run configuration; create `run_id`; record component versions; start the pipeline; stop at the initial manual checkpoint when configured | `PipelineOrchestrator` / CLI | One local Python process; manually invoked command; cron remains post-acceptance | Run arguments + config versions -> run manifest and initial run status | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.6, §6–7; [`ARCHITECTURE.md`](../architecture/ARCHITECTURE.md) | ADR-016; active source/config versions | Minimal run manifest is not yet frozen; full [`COLLECTION_RUN_SPEC.md`](COLLECTION_RUN_SPEC.md) is parked | **Missing P0:** command, manifest, checkpoint, and terminal-state contract |
| 1 | Indeed discovery + detail capture | Expand the accepted query inventory; call the Apify actor with query/geography input; one call returns full job detail directly (`jobKey`, canonical `jobUrl`, structured `location`, `expired`/`isRemote`, description) — no separate discovery-then-detail split | `IndeedApifyAdapter` implementing `SourceAdapter` | REST API / `apify-client` call to `borderline/indeed-scraper`, authenticated via a personal Apify token in a gitignored `.env`; code controls the frozen queries | Sourcing config + query definition -> full `RawJobRecord`s (discovery and detail combined) | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.1; [`SOURCE_ADAPTER_SPEC_MVP.md`](SOURCE_ADAPTER_SPEC_MVP.md) §2 | [`SOURCING_POLICY_MVP.md`](SOURCING_POLICY_MVP.md); [`SOURCING_CONFIG_MVP.md`](SOURCING_CONFIG_MVP.md) §3/§4/§6; [`queries-v0.1.yaml`](../../config/sourcing/queries-v0.1.yaml); [`indeed-de-v0.1.yaml`](../../config/sourcing/sources/indeed-de-v0.1.yaml) (still describes the superseded MCP source config; not yet updated for the Apify adapter) | Discovery + detail portions of `RawJobRecord`, both from the same call | **Partial:** `IndeedApifyAdapter` and `LinkedInApifyAdapter` implemented in `pipeline/adapters/` (2026-08-31), field mapping validated offline against both sources' saved fixtures via `pipeline/validate_adapters_against_fixtures.py` (0 mapping problems, no live Apify calls made); `indeed-de-v0.1.yaml` rewritten for the Apify actor and `linkedin-extension-v0.1.yaml` replaced by `linkedin-apify-v0.1.yaml` (enabled in `sourcing-v0.1.yaml`), closing the config gap this row previously flagged. Still open: no live `capture()` call has been run against either actor yet (only the fixture-fed mapping path is exercised); `collection_run_id` is populated by a placeholder `RunContext` stub (`pipeline/source_adapter.py`), not the still-undesigned Stage 0 run manifest (row 0); and neither adapter is wired into an orchestrator — `capture()` must currently be invoked directly. |
| 2 | Raw persistence | Compute the deterministic content hash; append the already-complete `RawJobRecord` (from either active `SourceAdapter`) to its per-source JSONL file before downstream processing — no separate detail-capture call happens here, since discovery and detail were already combined in stage 1 | `RawJobRepository` | Deterministic hashing + append-only JSONL writer, per [`SOURCE_ADAPTER_SPEC_MVP.md`](SOURCE_ADAPTER_SPEC_MVP.md) §1 Physical storage layout | `RawJobRecord` (from stage 1) -> persisted line in `data/raw/source_records/{source}.jsonl` | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.4; [`SOURCE_ADAPTER_SPEC_MVP.md`](SOURCE_ADAPTER_SPEC_MVP.md) §1 | ADR-016 (JSONL-only persistence) | `RawJobRecord` must include raw content, hash, IDs/URLs, timestamps, provenance, and capture status | **Resolved 2026-08-31:** `RawJobRecord` = the common `SourceRecord` contract, persisted as `data/raw/source_records/{source}.jsonl` (one JSON object per line, append-only, plus a verbatim `raw_payload` field) — [`SOURCE_ADAPTER_SPEC_MVP.md`](SOURCE_ADAPTER_SPEC_MVP.md) §1 |
| 3 | Pre-extraction deduplication | Look up `source + source_job_id`; fall back to resolved canonical URL when the source ID is unavailable; compare raw content hash; classify `new`, `duplicate_unchanged`, or `changed`; skip all LLM calls for unchanged duplicates | `RawJobDeduplicator` / identity index | Deterministic JSONL lookup; no semantic or cross-source similarity matching | Persisted `RawJobRecord` + prior identity/hash records -> dedup outcome | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.2 | Identity rules in [`JOB_SCHEMA_MVP.md`](JOB_SCHEMA_MVP.md) and ADR-016 | Dedup outcome fields belong to the raw/run processing record; canonical `Job` is created only for `new` or `changed` | **Defined conceptually:** exact physical record/index representation remains part of the Raw/Run contracts |
| 4 | LLM Job extraction | For `new` or `changed` records, send the JD text to one extraction model call for the JD-derived fields; assemble the rest deterministically; return flat Job JSON; do not assess candidate fit; preserve raw-to-structured linkage | `JobExtractor` | One programmatic LLM call per eligible dedup outcome (`description`/`responsibilities`/`qualifications_requirements`/`description_status`/`work_mode` only) plus deterministic passthrough/derivation for the rest; versioned extraction prompt and model configuration | `RawJobRecord` -> flat `Job` JSON or extraction failure | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.3; [`JOB_EXTRACTION_PROMPT_MVP.md`](JOB_EXTRACTION_PROMPT_MVP.md); ADR-015 | Do not invent missing facts; do not perform HD/Fit reasoning during extraction | [`JOB_SCHEMA_MVP.md`](JOB_SCHEMA_MVP.md) | **Drafted 2026-09-01, not fixture-validated:** prompt, field responsibility split, and output/failure contract defined in [`JOB_EXTRACTION_PROMPT_MVP.md`](JOB_EXTRACTION_PROMPT_MVP.md); request envelope and model configuration still pending Stage 0's run manifest |
| 5 | Minimal input guard / Assessment Eligibility | Parse the extraction output as JSON; check required identity/version fields; check raw JD linkage; require non-empty string values for `description`, `responsibilities`, and `qualifications_requirements`; return `Eligible` or `Blocked` | `AssessmentEligibilityChecker` called by the orchestrator | Small deterministic function; no full Data Validation, semantic completeness check, or optional-fact detection | Extracted Job + raw evidence + Profile/policy/prompt/model/schema versions -> eligibility result | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.3.1 | Optional facts such as compensation/language/travel are not eligibility gates; their absence is handled by the assessment policies | Eligibility result: `assessment_eligibility`, rules version, blocking reasons, checked time | **Defined:** executable schema/function still needs implementation |
| 6 | Hard Disqualifier assessment | Supply the canonical Job, raw JD snapshot, fixed Candidate Profile, and frozen HD policy; evaluate every rule; return per-rule `Pass` / `Fail` / `Unknown` / `Flag`, evidence, reason, and overall decision | `HardDisqualifierEvaluator` | First assessment LLM call; one call for every `Eligible` Job; invalid call/output becomes a visible failed result with no automatic retry | Eligible Job assessment envelope -> HD result | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.5; [`EVAL_EXECUTION_PROMPT.md`](../llm_eval/EVAL_EXECUTION_PROMPT.md) §4 | [`HARD_DISQUALIFIER_POLICY.md`](../llm_eval/HARD_DISQUALIFIER_POLICY.md) v0.2 | HD portion of [`EVAL_RESULT_SCHEMA_MVP.md`](../llm_eval/EVAL_RESULT_SCHEMA_MVP.md) | **Defined in Markdown:** executable JSON Schema/Pydantic model and fixed Candidate Profile contract remain P0 |
| 7 | HD branch decision | Inspect the validated HD result; when any rule is `Fail`, set `Exclude`, retain the exclusion evidence, and skip Fit; otherwise proceed to Fit, including `Unknown` or `Flag` | `AssessmentOrchestrator` branch | Deterministic conditional; no additional model call | HD result -> `skip Fit` or `run Fit` | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.5 | Overall-decision rule in [`HARD_DISQUALIFIER_POLICY.md`](../llm_eval/HARD_DISQUALIFIER_POLICY.md) §2 | Cross-field rules and `fit_skip_reason` in [`EVAL_RESULT_SCHEMA_MVP.md`](../llm_eval/EVAL_RESULT_SCHEMA_MVP.md) | **Defined** |
| 8 | Capability Fit assessment | For jobs with no confirmed HD `Fail`, compare the same Job/JD evidence with the fixed Candidate Profile; identify direct/transferable matches, one key gap, material unknowns, and one categorical Fit label | `CapabilityFitEvaluator` | Second, separate assessment LLM call; no numeric score or application recommendation | Proceeding HD result + Job/JD + Candidate Profile -> Fit result | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.5; [`EVAL_EXECUTION_PROMPT.md`](../llm_eval/EVAL_EXECUTION_PROMPT.md) §5 | [`CAPABILITY_FIT_POLICY.md`](../llm_eval/CAPABILITY_FIT_POLICY.md) v0.2 | Fit portion of [`EVAL_RESULT_SCHEMA_MVP.md`](../llm_eval/EVAL_RESULT_SCHEMA_MVP.md) | **Defined in Markdown:** executable schema and fixed Candidate Profile contract remain P0 |
| 9 | Result assembly and JSONL persistence | Combine identity, versions, eligibility, applicable HD/Fit output, skip/failure state, timestamps, and evidence; append without overwriting prior runs; keep every duplicate, blocked, excluded, completed, and failed outcome locatable | `EvaluationResultAssembler` + `JsonlRepository` | Deterministic assembly and append-only JSONL writing under ADR-016 | Stage outputs -> canonical evaluation/run JSONL records | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.4, §4.6, §4.8; ADR-016 | Version preservation and no-overwrite rules in the Eval prompt/policies | [`EVAL_RESULT_SCHEMA_MVP.md`](../llm_eval/EVAL_RESULT_SCHEMA_MVP.md); Raw/Run physical schemas still missing | **Partial:** evaluation result contract exists; physical files and run/raw layouts remain P0 |
| 10 | Run reconciliation | Count discovered, captured, duplicate, structured, blocked, disqualified, Fit-evaluated, completed, failed, and human-review-needed outcomes; ensure every discovered item has one locatable outcome | `RunReconciler` | Deterministic counters over JSONL records | Run records -> reconciliation summary and terminal run status | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.8, §7 | No silent record loss; full CollectionRun state machine remains parked | Minimal run summary contract is not yet frozen | **Missing P0:** run manifest/summary and terminal-state contract |
| 11 | Excel human-review export | Produce one review row per relevant Job with identity, provenance, eligibility/failure state, HD/Fit evidence, unknowns, and editable human review fields; never treat Excel as the system of record | `HumanReviewExporter` | Deterministic JSONL-to-XLSX export after the run; no implicit re-import | Canonical JSONL records -> Excel review workbook | [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.7; [`EVAL_EXECUTION_PROMPT.md`](../llm_eval/EVAL_EXECUTION_PROMPT.md) §6 | Human decision remains separate from Fit; source/model records are immutable | Eval result schema exists; review row/edit contract is not yet frozen | **Missing P1:** Excel column contract and explicit feedback import/update behavior |

## 3. Component Call Boundaries

The normal `new` / `changed` path uses three model calls at most:

```text
1. Job extraction
2. Hard Disqualifier
3. Capability Fit only when HD has no confirmed Fail
```

`duplicate_unchanged` uses zero model calls. `Blocked` after extraction uses
only the extraction call and is not sent to either assessment evaluator.

## 4. Contract Dependency Order

The remaining implementation contracts should be completed in this order:

1. Run command/manifest and physical JSONL layout;
2. ~~`RawJobRecord` schema~~ — resolved 2026-08-31, see §2 row 2;
3. ~~extraction prompt and output contract~~ — drafted 2026-09-01, see
   [`JOB_EXTRACTION_PROMPT_MVP.md`](JOB_EXTRACTION_PROMPT_MVP.md);
4. fixed Candidate Profile artifact/version contract;
5. executable Assessment result schema/model;
6. review export columns and feedback behavior.

Full Data Validation, automatic retry/repair, cron, LinkedIn, SQLite, semantic
deduplication, and partial-JD classification remain post-MVP.
