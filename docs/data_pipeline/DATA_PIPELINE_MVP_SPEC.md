# Data Pipeline MVP Design Spec

Status: MVP v0.9 — accepted Indeed + LinkedIn pipeline for review, both
sourced via Apify actors (ADR-017, ADR-018).
Updated: 2026-08-31 — LinkedIn un-parked (ADR-017); Indeed MCP connector
replaced by an Apify actor (ADR-018)

## 1. Purpose

Run Indeed discovery, capture, pre-extraction deduplication, structured
extraction, two-stage
LLM evaluation, persistence, and human review as one
traceable pipeline. The MVP must make every discovered job accountable without
introducing production-scale infrastructure. This document is the single
source of truth for MVP scope and build progress. Full future-state designs
remain parked until the MVP is running (see §5).

## 2. Scope Decisions

The 2026-08-20 design decisions remain in force, with the minimum-pipeline
boundary accepted on 2026-08-27:

1. **The LLM evaluator reads the original JD evidence and does not require a
   normalized six-entity recruiting model.** A minimal structured-extraction
   step is still required to produce the accepted flat `Job`
   contract. It answers “what does the posting say?” and must not perform
   candidate matching. The `JobCondition` / `JobRequirement` /
   `JobResponsibility` child-entity design remains parked because it would
   duplicate work without improving the MVP decision loop.
2. **Indeed and LinkedIn are both sourced via paid Apify Store actors, not a
   Cowork MCP connector.** The Indeed MCP connector (`search_jobs` /
   `get_job_details`) was the only validated Indeed access until 2026-08-31;
   it is now superseded by the `borderline/indeed-scraper` Apify actor
   (ADR-018) for the same reasons LinkedIn adopted
   `curious_coder/linkedin-jobs-scraper` (ADR-017) — see
   [`SOURCE_ADAPTER_SPEC_MVP.md`](SOURCE_ADAPTER_SPEC_MVP.md) §2 (Indeed,
   active) and §3 (Indeed MCP, superseded but documented). "Decoupled from
   Cowork" now means no Cowork dependency for either source, not just no
   human pasting prompts into a chat. The scraping layer is built behind a
   `SourceAdapter` interface (§4.1) so either implementation can be swapped
   without touching anything downstream.
3. **Pipeline responsibilities remain explicit even when their implementation
   is small.** The MVP combines components where practical, but retains minimal
   evidence, a minimal technical input guard, deduplication, processing status,
   reconciled counts, and human feedback. These make the LLM Eval reproducible
   and reviewable without adding production infrastructure.

## 3. MVP Goal

One repeatable run that: executes the accepted Sourcing Policy against Indeed →
captures minimally sufficient source evidence → deduplicates the raw capture →
extracts a flat `Job` record → runs the minimal input guard → runs Hard
Disqualifier and then Capability Fit →
persists the result and processing state → presents it for human review →
records minimal run-quality metrics. No dashboard, no multi-source
reconciliation, and no normalized child-entity model.

## 4. Engineering Design

### 4.1 Indeed Source Adapter: Discovery and Capture

```python
class SourceAdapter(Protocol):
    def fetch_jobs(self, query: QueryDefinition) -> list[RawJobRecord]: ...
```

- First MVP implementation: `IndeedApifyAdapter`, calling the Apify Store
  actor `borderline/indeed-scraper` via its REST API / `apify-client` SDK,
  authenticated with a personal Apify token from a gitignored `.env`
  (`SOURCE_ADAPTER_SPEC_MVP.md` §2; adopted 2026-08-31, ADR-018, replacing `IndeedMCPAdapter`). One call per
  query returns discovery and full detail together as structured JSON —
  `jobKey` (Indeed's real job key), a canonical `jobUrl` needing no redirect
  resolution, a structured `location` object, and `expired`/`isRemote`
  boolean fields. The previously validated `IndeedMCPAdapter`
  (`search_jobs` → `get_job_details` → raw-HTTP redirect resolution of the
  `to.indeed.com` short link → markdown parsing) remains documented in
  `SOURCE_ADAPTER_SPEC_MVP.md` §3 but is superseded, not deleted.
- Query vocabulary and geography come from
  [`SOURCING_POLICY_MVP.md`](SOURCING_POLICY_MVP.md)
  (unchanged, already Accepted). At runtime, code deterministically expands
  and executes the accepted query groups and filters. An Agent is not asked to
  reinterpret or regenerate the Sourcing Policy on every run. Agent-assisted
  query expansion is post-MVP unless explicitly run as a separate experiment.
- Discovery and detail are captured together per job (source job reference,
  URL, query provenance, capture status, JD text, content hash, and
  adapter/parser version) — there is no separate detail-capture call for this
  adapter, unlike the superseded MCP connector.
- **LinkedIn Source Adapter:** second MVP implementation,
  `LinkedInApifyAdapter`, calling the Apify Store actor
  `curious_coder/linkedin-jobs-scraper` via its REST API / `apify-client` SDK
  (`SOURCE_ADAPTER_SPEC_MVP.md` §4; un-parked 2026-08-31, ADR-017). Same single-call discovery+detail shape as the
  Indeed Apify adapter above. The Chrome Extension design remains parked
  (§5 below).

### 4.2 Pre-Extraction Deduplication

Deduplication runs after the raw capture has been persisted and the real Indeed
`source_job_id` has been recovered, but before any LLM extraction call. This
prevents an unchanged duplicate from consuming extraction or assessment calls
while retaining an auditable raw discovery/capture outcome.

The deterministic identity is `source + source_job_id`. When
`source_job_id` is unavailable, the resolved canonical `source_url` is the MVP
fallback; weaker company/title/location similarity does not automatically
merge records.

The deduplication outcome is:

| Outcome | Condition | Next action |
|---|---|---|
| `new` | No existing canonical record has the identity. | Continue to LLM extraction. |
| `duplicate_unchanged` | Identity exists and the captured raw-content hash is unchanged. | Record the duplicate outcome; skip extraction, HD, and Fit. |
| `changed` | Identity exists but the captured raw-content hash changed. | Continue to extraction and produce the updated current `Job` result. |

The same rule applies within a run and against prior persisted runs. Every raw
capture remains accountable even when downstream processing is skipped.

### 4.3 Structured Extraction and Minimal Technical Guard

Use [`JOB_SCHEMA_MVP.md`](JOB_SCHEMA_MVP.md) as the flat
`Job` contract. For the MVP, one dedicated LLM extraction call turns the
connector markdown and JD text into this contract. This choice prioritizes
delivery speed and the extraction quality already observed in two manual
trials; optimizing token cost through a more complex deterministic parser is
post-MVP work. Extraction must only describe posting facts; it must not judge
candidate fit. `description`, `responsibilities`,
`qualifications_requirements`, and their source evidence remain available to
the evaluator. No `JobCondition` / `JobRequirement` / `JobResponsibility`
child records are introduced for MVP.

Deterministic code remains responsible for preserving the raw connector
response, calculating hashes, parsing only transport-level metadata where
needed, and checking that the LLM response is parseable JSON. It must not
silently repair or invent extracted facts. A response that cannot be parsed is
recorded as an extraction failure.

The first runnable MVP has no separate Data Validation stage. It does not check
all field types, enums, ranges, cross-field consistency, partial-JD quality, or
semantic completeness. Those checks are deferred until the end-to-end flow is
working. The only pre-assessment protection is the minimal technical guard in
§4.3.1.

#### 4.3.1 Assessment Eligibility Contract

Assessment Eligibility is a minimal deterministic code guard executed after
extraction for a record whose pre-extraction deduplication outcome was `new` or
`changed`. The LLM evaluator does not decide
whether it should start. The Pipeline Orchestrator calls the Hard Disqualifier
when this gate returns `Eligible`.

The minimum assessment input is:

- a traceable job identity: `job_id`, `title`, `company`, `source_url`, and
  `captured_at`;
- the raw JD content captured in this run, retained as the original connector
  markdown/text plus a content hash; the URL identifies the source but does
  not replace the captured content snapshot;
- non-empty string values for `description`, `responsibilities`, and
  `qualifications_requirements` after whitespace trimming;
- no unresolved mismatch among the captured JD, title, company, and resolved
  source page;
- a parseable extracted `Job` linked to the raw capture;
- a present, fixed Candidate Profile/CV version; and
- present Hard Disqualifier, Capability Fit, prompt, model-configuration, and
  output-schema versions.

Eligibility has exactly two states:

| State | Meaning | Orchestrator action |
|---|---|---|
| `Eligible` | The extracted JSON is parseable and every required input listed above is present. | Start Hard Disqualifier. |
| `Blocked` | Core evidence or execution context is missing, mismatched, failed, or unreliable, so policy execution would require guessing. | Do not call an assessment model; record blocking reasons and mark the job for human review. The MVP performs no automatic retry, repair, or follow-up processing. |

Missing compensation, an explicit experience-year floor, contract detail,
language detail, credential detail, travel percentage, work mode, publication
date, or detailed company background does not by itself block assessment. When
the source JD does not disclose such a fact, the applicable Hard Disqualifier
rule controls whether the result is `Pass`, `Unknown`, or `Flag`; missing facts
must never be converted into an inferred `Fail`.

`Blocked` applies when, for example, there is no captured JD; `description`,
`responsibilities`, or `qualifications_requirements` is null, not a string, or
empty after whitespace trimming; there is an unresolved description–URL /
company / title mismatch; extraction cannot be parsed; raw evidence is
unavailable; or a required Candidate Profile, policy,
prompt, model, or schema version is missing.

For MVP, code checks only JSON parseability and presence, not full schema
conformance or whether a string is a semantically complete or high-quality description. The initial manual review
checkpoint detects poor-but-non-empty extraction. Dedicated partial-JD,
truncation, and semantic completeness detection is post-MVP and should be added
only if observed failures justify it.

The gate emits at least:

```yaml
assessment_eligibility: Eligible | Blocked
eligibility_rules_version: assessment-eligibility-v0.1
blocking_reasons: []
checked_at: datetime
```

Source non-disclosure and pipeline failure remain distinct: undisclosed
optional facts are handled by the Hard Disqualifier policy after entry;
pipeline failure produces `Blocked` when it compromises required structural
input.

### 4.4 Storage

JSONL only. Keep append-only job/evaluation records plus one unified output per
run. Persist source provenance, minimal raw evidence/reference, processing
statuses, policy/prompt/model/schema versions, and human review fields. No
SQLite and no full `SourcingConfig` lifecycle for MVP; the active config file
is retained with a content hash or version identifier on each run.

### 4.5 LLM Evaluation: Hard Disqualifier, then Capability Fit

Turn [`EVAL_EXECUTION_PROMPT.md`](../llm_eval/EVAL_EXECUTION_PROMPT.md)'s
per-record instructions into programmatic model calls (Claude API, not a
Cowork paste-and-run), consuming: the `Job` record, the fixed Candidate
Profile, and the existing
[`HARD_DISQUALIFIER_POLICY.md`](../llm_eval/HARD_DISQUALIFIER_POLICY.md)
and
[`CAPABILITY_FIT_POLICY.md`](../llm_eval/CAPABILITY_FIT_POLICY.md).
Evaluation has two explicit stages and two independently validated model-call
boundaries:

1. **Hard Disqualifier call.** Apply every accepted rule and return per-rule
   `Pass` / `Fail` / `Unknown`, reasons, and quoted evidence. A confirmed
   `Fail` ends evaluation and Capability Fit is skipped. `Unknown` does not
   silently become `Fail`; it follows the policy's review rule.
2. **Capability Fit calls.** Only for jobs without a confirmed disqualifying
   `Fail`. Per `capability-fit-v0.3`, one CV-blind call decomposes the
   JD into hard skills, marks the three most central ones, and records the
   industry as a parallel variable. A second, core-blind call gives every skill
   and the industry one of five evidence states against the Candidate Profile
   (`done` / `participated` / `adjacent` / `unconfirmed` / `not_done`, with
   cited evidence). Code then derives `Strong Fit` / `Plausible Fit` /
   `Weak Fit` / `Unclear` from the three core skills.

Clear deterministic conditions may be code-assisted after extraction (for
example, a numeric salary below an accepted threshold), but semantic policy
interpretation remains in the dedicated LLM Eval. Output fields follow
`EVAL_EXECUTION_PROMPT.md` and retain `evaluated_at`, model, prompt, policy,
and run identifiers.

Keeping the calls separate enforces the non-compensatory branch, avoids Fit
token use for excluded jobs, permits stage-specific validation and failure
isolation, and
allows Hard Disqualifier and Capability Fit quality, cost, and failures to be
measured independently. A Fit prompt change must not alter or force a rerun of
an otherwise identical Hard Disqualifier result.

### 4.6 Processing Status and Orchestration

A single script, no Airflow/Dagster:

`discover → capture/persist raw → dedupe → structure → minimal input guard → Hard Disqualifier →
Capability Fit → persist → human review output`.

Cron may later trigger a headless Claude Code / Agent SDK run of this script.
The MVP does not implement the full `CollectionBatch` / `CollectionRun` state
machine, but it retains three separate status dimensions per job:

- `pipeline_status`: `discovered`, `captured`, `structured`,
  `evaluated`, `completed`, or an explicit failure state;
- `evaluation_status`: Hard Disqualifier outcome and, when applicable,
  Capability Fit outcome;
- `review_status`: `pending`, `accepted`, `rejected`, or `corrected`.

Every failure records its stage and reason and is marked for human review. The
MVP does not automatically retry, repair, or otherwise process failed records.
This prevents silent record loss without adding recovery orchestration.

### 4.7 Human Review Output and Feedback

One unified file per run (JSONL, plus an Excel export for human review) with
one row per job: job identity, capture provenance, input-guard result, full
two-stage evaluation, evidence, unknowns, and processing status. The reviewer
can record `accepted`, `rejected`, or `corrected`, plus an optional correction
reason. Human application choice remains separate from Capability Fit.

The export is not a Capability-Fit-only view. Every captured job remains
locatable. Hard-Disqualifier `Exclude` rows are included with the failed rule,
evidence, and `fit_skip_reason=HardDisqualifierFail`; blocked and failed rows
are included with their stage and reason. Separate worksheet views may improve
review ergonomics, but they must derive from the same complete run output.

### 4.8 Minimal Observability and Reconciliation

Each run records `run_id`, timestamps, config/policy/prompt/model versions,
token/call cost where available, and counts for discovered, captured,
structured, duplicate, disqualified, fit-evaluated, needs-review, completed,
and failed jobs. The counts must reconcile: every discovered job ends in a
locatable outcome. No production monitoring stack or alerting system is built
for MVP.

## 5. Parked for Post-MVP

Not deleted — each item stays fully designed in its owning file, marked
`Status: Parked for MVP` there, and can be picked back up when the MVP is
running and a concrete need appears.

| Parked item | Owning file | Why parked |
|---|---|---|
| Full `CollectionBatch` / `CollectionRun` audit state machine and reconciliation checklist | `COLLECTION_RUN_SPEC.md` | MVP retains per-job status and run counts, but the full multi-run audit model is unnecessary overhead. |
| Partial-JD, truncation, and semantic-completeness classifier | This spec §4.3.1 | MVP checks required strings structurally and uses the initial manual checkpoint; build a classifier only if observed failures justify it. |
| LinkedIn Chrome Extension adapter | `SOURCE_ADAPTER_SPEC_MVP.md` §5 | Superseded for MVP by the LinkedIn Apify Adapter (§4, ADR-017, 2026-08-31) — not required now that a non-interactive, non-browser LinkedIn capture path exists. Revisit only if a logged-in-account capture need reopens it post-MVP. |
| Indeed MCP connector adapter | `SOURCE_ADAPTER_SPEC_MVP.md` §3 | Superseded for MVP by the Indeed Apify Adapter (§2, ADR-018, 2026-08-31) — not required now that a structured, non-Cowork-dependent Indeed capture path exists. Kept documented for its redirect-resolution technique in case the Apify path becomes unavailable. |
| `JobCondition` / `JobRequirement` / `JobResponsibility` child-entity model; `SourcingConfig` / `CollectionBatch` / `CollectionRun` full field tables | `DATA_DICTIONARY.md` | MVP performs only the flat structured extraction required by the accepted `Job` schema; the normalized child model would add complexity without testing a new hypothesis. |
| Six-entity recruiting-side contract (`CollectionRun → SourceRecord → Job → JobCondition/JobRequirement/JobResponsibility`) | Recruiting-side data spec (not published) | Superseded for MVP by the flat schema in `JOB_SCHEMA_MVP.md`. |
| `SourcingConfig` lifecycle beyond a retained content hash/version, cross-source dedup/queue rules, SQLite storage decision | `SOURCING_CONFIG_MVP.md` §2, §7, §10 | One source, one active config, and one storage format are enough. §3 (Indeed active), §4 (geography/language), and §6 (query groups) remain the MVP config values. |

## 6. Progress Tracker

Update the Status column as work lands; treat this table, not memory or chat
history, as the current build state.

| # | Step | Owning design | Status |
|---|---|---|---|
| 1 | `SourceAdapter` interface + deterministic Indeed Policy execution and capture | `SOURCE_ADAPTER_SPEC_MVP.md` §2, §4.1 above | In progress — `SourceAdapter`, `IndeedApifyAdapter`, `LinkedInApifyAdapter` implemented in `pipeline/`; field mapping validated against saved fixtures only, no live `capture()` call made yet, wired into the orchestrator (item 8) |
| 2 | Persist raw capture and deduplicate by `source + source_job_id` before LLM work | §4.2, §4.4 above | Done (offline-validated) — `RawJobRepository` (`pipeline/raw_job_repository.py`) and `RawJobDeduplicator` (`pipeline/dedup.py`, Layer 1 per `DEDUPLICATION_SPEC_MVP.md`) both implemented and covered by `pipeline/validate_phase_a.py`/`validate_phase_d.py` |
| 3 | Flat `Job` LLM extraction + parseability check for `new` / `changed` records | `JOB_SCHEMA_MVP.md`, §4.3 above | Done (offline-validated) — `JobExtractor` (`pipeline/job_extractor.py`) implements `JOB_EXTRACTION_PROMPT_MVP.md` §5 verbatim; structural failure modes covered in `pipeline/validate_phase_c.py`. Not yet exercised against a live JD (blocked on an Anthropic API key, see §9) |
| 3a | Minimal Assessment input guard | §4.3.1 above | Done (offline-validated) — `AssessmentEligibilityChecker` (`pipeline/eligibility.py`) |
| 4 | Minimal evidence, status, and version persistence in JSONL | §4.4, §4.6 above | Done (offline-validated) — `pipeline/result_repository.py` (`data/jobs/jobs.jsonl`, `data/evaluations/evaluations.jsonl`, both append-only and gitignored) |
| 5 | Programmatic Hard Disqualifier branch | `EVAL_EXECUTION_PROMPT.md`, Hard Disqualifier policy, §4.5 above | Done (offline-validated) — `HardDisqualifierEvaluator` (`pipeline/hard_disqualifier.py`); Candidate Profile contract resolved as a reviewable draft (`config/candidate_profile/candidate-profile-v0.1.yaml`). Not yet exercised against a live model call |
| 6 | Programmatic Capability Fit branch for non-disqualified jobs | `EVAL_EXECUTION_PROMPT.md`, Capability Fit policy, §4.5 above | Done (offline-validated) — `CapabilityFitEvaluator` (`pipeline/capability_fit.py`), including the direct-vs-transferable schema gate. Not yet exercised against a live model call |
| 7 | Unified JSONL + Excel human-review output and feedback fields | §4.7 above | Done (offline-validated), minimal column set plus a "Fit Skill Map" sheet (one row per job × requirement, Fit policy §9.1) — `HumanReviewExporter` (`pipeline/review_export.py`) |
| 8 | Single-process orchestration, per-job failures, and reconciled run counts | §4.6–4.8 above | Done (offline-validated) — `PipelineOrchestrator` (`pipeline/orchestrator.py`) + `run_pipeline.py` CLI wire every stage above in order, including the manual checkpoint (§7 below) and the `RunReconciler` (`pipeline/reconciliation.py`); full fake end-to-end run exercised in `pipeline/validate_phase_d.py` |
| 9 | End-to-end manual run on a small fixed Eval batch, output reviewed | §7 below | Blocked — needs an `ANTHROPIC_API_KEY` (Apify token already present in `.env`). Every stage above is code-complete and offline-validated with zero live calls; this is the only remaining step before a real run |
| 10 | Optional headless Claude / cron trigger wiring after manual acceptance | §4.6 above | Not started (post-MVP, correctly deferred until item 9 succeeds) |

Provider/model selection for items 3, 5, and 6 is decoupled into
`config/models/model-config-v0.1.yaml` per `MODEL_CONFIG_MVP.md` — only the
`anthropic` provider has a real `ModelClient` implementation
(`pipeline/model_client.py`) today, but none of the three stages above import
a provider SDK directly, so adding another provider does not require
revisiting this table.

## 7. MVP Acceptance Criteria

1. One command processes a small batch of real, appropriately protected input
   end to end without a human pasting prompts into Cowork.
2. Every discovered job has a locatable terminal or human-review outcome; run
   counts reconcile without silent drops.
3. Every `Job` record traces back to a `source_url`, capture time, and retained
   minimal source evidence/reference.
4. Duplicate scrapes of the same `source_job_id` do not create duplicate
   `Job` records, and unchanged duplicates do not trigger extraction or
   assessment model calls.
5. Extraction output is parseable JSON and passes the minimal required-input
   guard before evaluation; full data-quality validation is not an MVP gate.
6. Only `Eligible` records enter Hard Disqualifier;
   `Blocked` records retain explicit reasons and receive no assessment call.
7. Missing optional source facts remain visible as policy-level
   `Unknown` / `Flag` outcomes rather than becoming inferred `Fail` results.
8. Hard Disqualifier and Capability Fit run per the existing branch rule
   (Fit skipped after a confirmed Fail).
9. Every material judgment carries evidence or is explicitly `Unknown`.
10. Re-running the same input twice does not produce unintended duplicates
   in the output.
11. A failure on one job produces a locatable status/error record and does not
   silently drop the record or crash the batch.
12. Policy, prompt, model, schema, config, and run identifiers are retained.
13. A human can review each result, record `accepted` / `rejected` /
    `corrected`, and keep the application decision separate from Fit.

## 8. Document Index (Current State)

| File | Role now |
|---|---|
| `DATA_PIPELINE_MVP_SPEC.md` (this file) | Canonical MVP design and progress tracker |
| `MVP_WORKFLOW_STAGE_CONTRACT_MAP.md` | Stage-by-stage implementation, component, rule, and contract navigation map |
| `SOURCING_POLICY_MVP.md` | Active — search vocabulary, geography, scope rules |
| `JOB_SCHEMA_MVP.md` | Active — the MVP `Job` schema |
| `SOURCE_ADAPTER_SPEC_MVP.md` | Active for §2 (Indeed via Apify) and §4 (LinkedIn via Apify); §3 (Indeed MCP) and §5 (Chrome Extension) superseded/parked |
| `SOURCING_CONFIG_MVP.md` | Active for §3/§4/§6 config values; rest parked |
| `COLLECTION_RUN_SPEC.md` | Parked |
| `DATA_DICTIONARY.md` | Parked |
| `../llm_eval/EVAL_EXECUTION_PROMPT.md` + both policy docs | Active — reused programmatically per §4.5, loaded verbatim at runtime by `pipeline/hard_disqualifier.py`/`capability_fit.py` |
| `JOB_EXTRACTION_PROMPT_MVP.md` | Draft v0.1 — implemented verbatim in `pipeline/job_extractor.py`; structural failure modes offline-validated, not yet fixture-validated against a live JD |
| `MODEL_CONFIG_MVP.md` | Active — implemented as `config/models/model-config-v0.1.yaml` + `pipeline/model_client.py`/`model_config.py` |

## 9. Remaining Build-Blocking Contracts

The stage sequence and Assessment Eligibility decision are now defined, and
every P0 contract below is resolved in code (offline-validated, not yet
exercised live — see §6 item 9). They do not expand MVP scope.

| Priority | Missing or conflicting contract | Required resolution |
|---|---|---|
| ~~P0~~ Resolved (minimal) | Run command and manifest | `pipeline/run_manifest.py::RunManifest` + `run_pipeline.py`: `run_id`, input/config versions, stage selection via `--sources`/`--max-per-source`, and the manual checkpoint (`PipelineOrchestrator._maybe_checkpoint`). Terminal states are the three per-job dimensions in `pipeline/reconciliation.py::RunCounts`, not a full state machine (correctly out of scope, §5). |
| ~~P0~~ Resolved 2026-08-31 | Raw capture schema | `RawJobRecord` = the common `SourceRecord` contract (`SOURCE_ADAPTER_SPEC_MVP.md` §1) persisted per the Physical storage layout subsection there: one `data/raw/source_records/{source}.jsonl`, append-only, one JSON object per line, plus a verbatim `raw_payload` field for source-specific facts not yet in the common contract. |
| ~~P0~~ Resolved 2026-09-01 (Draft) | Extraction contract | Per-job extraction prompt, field responsibility split (deterministic passthrough vs LLM-populated), output JSON shape, and parseability-failure handling defined in [`JOB_EXTRACTION_PROMPT_MVP.md`](JOB_EXTRACTION_PROMPT_MVP.md) and implemented in `pipeline/job_extractor.py`. |
| ~~P0~~ Resolved (Draft) | Candidate Profile contract | `config/candidate_profile/candidate-profile-v0.1.yaml`, loaded by `pipeline/candidate_profile.py` (version + content-hash, supplied as prompt text to both assessment calls). Content is a Claude-drafted first pass from the candidate's CV — every evidence item flagged `needs_review: true`, not yet human-confirmed. |
| ~~P0~~ Resolved | Executable assessment schema | `pipeline/assessment_schema.py` — Pydantic models mirroring `EVAL_RESULT_SCHEMA_MVP.md` §2/§4 exactly, including the cross-field validation rules. |
| Partial | Failure taxonomy | `ExtractionFailure`/`AssessmentCallFailure` carry a free-text `reason` per stage, surfaced in the review export — but there is no frozen set of stage-specific error *codes* yet. Automated retry and repair remain post-MVP, as designed. |
| Not resolved | Idempotency fingerprints | Layer-1 dedup (`content_hash`) correctly skips re-*extracting* an unchanged raw capture, but a rerun of an already-evaluated batch will call Hard Disqualifier/Capability Fit again — `data/evaluations/evaluations.jsonl` has no content_hash+policy+prompt+model dedup check before a model call. Acceptable for a first small manual run; revisit before any larger/repeated batch. |
| P1 | Review export/import behavior | Excel columns are frozen (minimal, `pipeline/review_export.py`); reviewer-edit re-import into the JSONL system of record is still not implemented. |
| ~~P1~~ Resolved | Executable schemas and fixtures | `pipeline/assessment_schema.py` plus `pipeline/validate_phase_a.py`/`_c.py`/`_d.py` cover valid, `Blocked`, extraction-failure, HD-Fail, and Fit-run cases end to end, offline. |
| P1 | Full Data Validation | Add field-type, enum, range, cross-field, partial-JD, and semantic-quality checks only after the first end-to-end run identifies which checks provide practical value. |

Cron, cross-source deduplication, parser/token optimization, dashboard, and
automated application remain post-MVP and are not blockers for the first
manual end-to-end run. LinkedIn was un-parked 2026-08-31 (ADR-017) and is now
in scope via the Apify adapter, §4.1 above. The only remaining blocker before
a real run is an `ANTHROPIC_API_KEY` (§6 item 9) — every stage is code-complete
and offline-validated with zero live calls made so far.
