# Data Dictionary

Status: Parked for MVP (2026-08-20) — see `DATA_PIPELINE_MVP_SPEC.md` §5.
The MVP evaluator reads raw JD text directly and does not consume the
structured `JobCondition` / `JobRequirement` / `JobResponsibility` extraction
defined here; MVP uses the flat schema in `JOB_SCHEMA_MVP.md`
instead. Design kept intact for when structured extraction is actually needed.
Principle: define concepts before selecting a storage format.

## Schema principles

- The normalized base layer stores job facts and evidence, not assessment conclusions.
- Preserve raw text alongside normalized typed values.
- Use `null/Unknown` for missing facts; absence of evidence is not `false`.
- Stable single-value facts are columns; repeatable requirements and responsibilities
  are child records.
- Assessment results are versioned separately because they depend on candidate profile,
  policy, prompt, and model versions.

## SourcingConfig

Grain: one immutable executable configuration version. Detailed settings and
open decisions are owned by `SOURCING_CONFIG_MVP.md`.

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| sourcing_config_id | string | yes | config | Stable versioned identity |
| sourcing_policy_version | string | yes | policy | Business-rule version used by the config |
| status | enum | yes | config | Draft / Active / Retired |
| enabled_sources | array | yes | config | Versioned source-config references |
| query_groups | array | yes | config | Active and inactive groups remain explicit |
| geography_config | object | yes | config | Candidate base, radius, remote eligibility |
| language_config | object | yes | config | German and English initially |
| time_window_config | object | yes | config | Initial and incremental rules |
| valid_from | datetime/null | no | config | Set on activation |
| valid_to | datetime/null | no | config | Null while active |
| created_at | datetime | yes | system | Creation time |
| change_reason | text | yes | config | Why this version exists |

## CollectionBatch

Grain: one logical collection cycle under one Policy/Config snapshot. Detailed
status rules are owned by `COLLECTION_RUN_SPEC.md`.

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| collection_batch_id | string | yes | collector | Stable batch identity |
| sourcing_policy_version | string | yes | config | Immutable snapshot reference |
| sourcing_config_version | string | yes | config | Immutable executable config reference |
| trigger_type | enum | yes | collector | Scheduled / Manual |
| triggered_by | string/null | no | collector | User/system identity |
| started_at | datetime | yes | collector | Start time |
| completed_at | datetime/null | no | collector | Null while running |
| status | enum | yes | collector | Pending / Running / Completed / Partial / Failed / Cancelled |
| summary_counts | object | yes | derived | Reconciled from child runs |

## CollectionRun

Grain: one source adapter × one query/config × one execution.

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| collection_run_id | string | yes | collector | Stable execution identity |
| collection_batch_id | string | yes | relationship | Parent logical collection cycle |
| source | string | yes | config | Indeed / LinkedIn initially |
| source_config_id | string | yes | config | Source-specific configuration |
| query_group_id | string/null | no | config | Null for direct/manual URL capture |
| query_id | string/null | no | config | Atomic source query identity |
| sourcing_policy_version | string | yes | config | Policy snapshot |
| sourcing_config_version | string | yes | config | Executable-config snapshot |
| adapter_version | string | yes | system | Adapter implementation version |
| parser_version | string | yes | system | Parser implementation version |
| trigger_type | enum | yes | collector | Scheduled / Manual / Retry |
| started_at | datetime | yes | collector | Start time |
| completed_at | datetime/null | no | collector | End time |
| status | enum | yes | collector | Pending / Running / Completed / Partial / Failed / Cancelled |
| cursor_in | object/null | no | collector | Source-specific input cursor |
| cursor_out | object/null | no | collector | Safely committed output cursor |
| counters | object | yes | derived | Required counters defined in Collection Run spec |
| retry_of_run_id | string/null | no | relationship | Failed/partial run being retried |
| completion_reason | string/null | no | collector | Required for non-completed terminal states |
| error_summary | object/null | no | collector | Structured error codes and counts |

## SourceRecord

Grain: one immutable capture/observation from one source. Multiple source
records may resolve to the same `job_id`.

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| source_record_id | string | yes | derived | Stable capture identity |
| source | string | yes | source data | Indeed / LinkedIn / historical import / manual |
| source_job_id | string/null | no | source data | Platform identifier when available |
| source_url | string | yes | source data | Original captured URL |
| resolved_url | string/null | no | collector | URL after redirects/canonicalization |
| collection_run_id | string | yes | collector | Identifies the source/query run |
| sourcing_policy_version | string | yes | config | Policy governing collection scope |
| sourcing_config_version | string | yes | config | Executable configuration used by the run |
| source_config_id | string | yes | config | Source-specific adapter configuration |
| query_id | string/null | no | config | Stable query/configuration identity |
| query_group_id | string/null | no | config | Role-family/query grouping |
| query_text_or_parameters | object/null | no | config | Preserve how the record was discovered |
| captured_at | datetime | yes | collector | Observation time |
| first_seen_at | datetime | yes | system | First system observation of the opening |
| adapter_version | string | yes | system | Indeed/LinkedIn adapter version |
| parser_version | string | yes | system | Extraction version |
| content_hash | string/null | no | derived | Detect unchanged versus updated content |
| raw_payload_reference | string/null | no | storage | Immutable evidence reference when retained |
| collection_status | enum | yes | collector | Captured / Partial / Failed / Closed / Unknown |
| parser_warnings | array | yes | collector | Explicit missing/ambiguous extraction findings |
| error_code | string/null | no | collector | Retryable or terminal capture error |

Each source's raw publication date is retained on its SourceRecord. After
cross-source identity is verified, `Job.first_published_at` is the earliest
credible raw date; repost dates remain separate.

## Job

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| job_id | string | yes | derived | Stable internal identifier |
| batch_id | string | yes | import | Import batch; separate from capture date |
| source | string | yes | source data | Source platform |
| source_url | string | no | source data | Original URL |
| source_job_id | string/null | no | source data | Platform job identifier when available |
| captured_at | datetime | no | source data | Collection time |
| function_raw | string/null | no | source data | Original or legacy function label |
| function_normalized | enum | yes | normalized | CSM / Growth / Marketing / PM-Coordinator / Other |
| company_raw | string | yes | source data | Original company name |
| company_normalized | string/null | no | normalized | Used for matching and deduplication |
| title_raw | string | yes | source data | Original job title |
| location_raw | string/null | no | source data | Original location wording |
| country_normalized | string/null | no | normalized | Normalized country |
| city_normalized | string/null | no | normalized | Normalized city |
| work_mode_normalized | enum/null | no | normalized | Remote / Hybrid / On-site / Field / Unknown |
| description_raw | text | yes | source data | Complete JD; missing/partial content is flagged |
| responsibilities_raw | text/null | no | source data | Original responsibility section |
| qualifications_raw | text/null | no | source data | Original requirement/qualification section |
| description_status | enum | yes | validation | Full / Partial / Preview-only / Missing |
| job_posted_at | datetime/null | no | source data | Publication time when available |
| job_status | enum | yes | source/normalized | Open / Closed / Expired / Unknown |
| first_published_at | datetime/null | no | normalized | Earliest credible date across verified sources |
| first_seen_at | datetime | yes | system | First system observation; not publication date |
| reposted_at | datetime/null | no | source/normalized | Repost observation/date; never overwrites first publication |

## DataQualityResult

Grain: one quality-check run per source/job version. Quality is stage-aware; a
field-level `Fail` is not an automatic record-level exclusion.

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| quality_result_id | string | yes | derived | Unique check result |
| job_version_id | string | yes | relationship | Checked source/job version |
| findings | array | yes | validation | Field, issue, evidence, severity, repairability |
| hard_disqualifier_readiness | enum | yes | validation | Ready / Flag / Blocked / Unusable |
| industry_gate_readiness | enum | yes | validation | Ready / Flag / Blocked / Unusable |
| capability_fit_readiness | enum | yes | validation | Ready / Flag / Blocked / Unusable |
| human_review_allowed | boolean | yes | validation | Missing automation inputs may still allow review |
| checked_at | datetime | yes | system | Check time |
| checker_version | string | yes | system | Deterministic/agent checklist version |

Missing compensation or another fact unused by a stage does not block that
stage. Missing or partial description/qualification content routes to human
review or blocks only the automated stages whose minimum evidence is absent.
`Unusable` is reserved for a non-job, irreparable record, not merely an
incomplete one.

## JobCondition

Grain: one record per `job_id`. These are reusable job facts, not gate results.

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| job_id | string | yes | relationship | References Job |
| career_stage_normalized | enum/null | no | normalized | Internship / Working-student / Entry / Mid / Senior / Lead / Executive / Unknown |
| career_stage_evidence | text/null | no | source evidence | Exact or minimally sufficient wording |
| min_years_required | decimal/null | no | normalized | Lower bound; only explicit mandatory years |
| years_requirement_status | enum | yes | normalized | Required / Preferred / Ambiguous / Not-stated |
| years_evidence | text/null | no | source evidence | Wording supporting the value/status |
| people_management_required | boolean/null | no | normalized | `null` means unknown; IC project leadership is not people management |
| people_management_evidence | text/null | no | source evidence | Required for true or ambiguous cases |
| employment_type | enum/null | no | normalized | Permanent / Fixed-term / Temporary / Agency / Internship / Working-student / Other / Unknown |
| contract_duration_months | integer/null | no | normalized | When explicitly stated |
| contract_evidence | text/null | no | source evidence | Original contract wording |
| salary_min | decimal/null | no | normalized | Numeric amount, not formatted text |
| salary_max | decimal/null | no | normalized | Numeric upper bound |
| salary_currency | string/null | no | normalized | ISO currency code where possible |
| salary_period | enum/null | no | normalized | Annual / Monthly / Hourly / Other |
| salary_component | enum/null | no | normalized | Base / OTE / Variable / Mixed / Unclear |
| salary_evidence | text/null | no | source evidence | Original published compensation wording |
| field_based | boolean/null | no | normalized | Primary working model; `null` when unclear |
| travel_percent_max | decimal/null | no | normalized | Explicit maximum percentage only |
| travel_requirement_status | enum | yes | normalized | Explicit / Occasional-ambiguous / Not-stated / Unknown |
| travel_evidence | text/null | no | source evidence | Original travel/field wording |

## JobRequirement

Grain: one record per atomic requirement. A job may have many requirements.

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| requirement_id | string | yes | derived | Stable within the source/job version |
| job_id | string | yes | relationship | References Job |
| category | enum | yes | normalized | Language / Credential / Tool / Domain / Education / Authorization / Experience / Other |
| requirement_raw | text | yes | source evidence | Exact or minimally sufficient wording |
| requirement_normalized | string | yes | normalized | E.g. German, PMP, Salesforce |
| mandatory_level | enum | yes | normalized | Required / Preferred / Ambiguous / Not-stated |
| value_normalized | string/number/null | no | normalized | E.g. C1, 5, Advanced |
| unit | string/null | no | normalized | E.g. years, CEFR |
| extraction_confidence | decimal/null | no | LLM/system | Confidence in extraction, not fit confidence |

## JobResponsibility

Grain: one record per atomic responsibility. Used primarily by Capability Fit.

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| responsibility_id | string | yes | derived | Stable within the source/job version |
| job_id | string | yes | relationship | References Job |
| responsibility_raw | text | yes | source evidence | Original responsibility wording |
| action_normalized | string/null | no | normalized | Core action, e.g. onboard, retain, implement |
| operating_object | string/null | no | normalized | Account, SaaS product, campaign, process, etc. |
| customer_or_beneficiary | string/null | no | normalized | Enterprise users, patients, partners, etc. |
| goal | string/null | no | normalized | Adoption, retention, revenue, delivery, etc. |
| product_context | string/null | no | normalized | Relevant product/domain context |
| delivery_model | string/null | no | normalized | Software onboarding, consulting, campaign execution, etc. |
| importance | enum | yes | normalized | Core / Supporting / Unknown |
| extraction_confidence | decimal/null | no | LLM/system | Confidence in extraction |

## CandidateProfile

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| profile_version | string | yes | project config | Versioned |
| constraints | object | yes | user | Language, salary, location, authorization |
| preferences | object | yes | user | Industry, work content, growth direction |
| evidence_items | array | yes | user | Verifiable experience evidence |

## Assessment

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| assessment_id | string | yes | derived | Unique assessment-run identifier |
| hard_constraints | array | yes | rule/LLM | Separate confirmed from unknown |
| capability_fit_label | enum/null | yes | system | Strong / Plausible / Weak / Unclear; null after a hard Fail |
| fit_policy_version | string | yes | system | Version of categorical Fit policy |
| hard_disqualifier_policy_version | string | yes | system | Version of gate policy |
| evidence | array | yes | system | Job evidence plus candidate evidence |
| unknowns | array | yes | system | Must not be guessed |
| model_version | string/null | yes | system | Null for rule-only assessments |
| prompt_version | string/null | yes | system | Null for rule-only assessments |
| application_protocol_version | string/null | no | policy | Required for prospective market-outcome analysis |

The current Assessment has no `attractiveness_score` or model-
generated `recommendation`. Legacy values are retained only in the historical
mapping and must not be silently copied into the current schema.

## HumanDecision

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| workflow_status | enum | yes | user/system | Unreviewed / Rejected / Applied; there is no Skip state |
| reason | text/null | no | user | Missing reason lowers label quality |
| reason_categories | array | no | annotation | May be multi-label |
| exploration_override | boolean | yes | annotation | Prevents treating exploration as a normal FN |
| label_quality | enum | yes | annotation | high / medium / low / exclude |
| decided_at | datetime/null | no | source data | Helps identify policy shifts |

Only `Unreviewed` enters the downstream human-review queue. Repost or updated
source evidence does not automatically reopen `Rejected` or `Applied`; a human
must explicitly reset the new version to `Unreviewed`.

## EvaluationAnnotation

| Field | Type | Required | Source | Notes |
|---|---|---:|---|---|
| human_fit_label | enum/null | yes | independent human review | Strong / Plausible / Weak / Unclear |
| known_problem | boolean | yes | retrospective audit | Whether a supported v1 problem is in scope |
| previous_failure_mode | enum/null | no | retrospective audit | Must be evidence-supported |
| repair_status | enum/null | no | evaluation | Repaired / Persisted / Not comparable |
| regression_status | enum/null | no | evaluation | No regression / New error / Not reviewed |
| error_category | enum/null | no | evaluation | Observable mismatch category |
| root_cause_owner | enum/null | no | evaluation | Policy / model-prompt / data / label / eval design / unclear |

## Legacy Mapping

Complete the legacy-workbook mapping in Week 1.

| Legacy sheet/column | New entity.field | Transformation | Risk |
|---|---|---|---|
| CSM/FA · Fit | LegacyAssessment.fit_score | preserve numeric, do not promote | Old single score mixes preferences and constraints |
| CSM/FA · My lean | LegacyAssessment.recommendation | preserve raw/normalize only for retrospective audit | Influenced by Round 1 policy; not current Assessment output |
| CSM/FA · Your call | HumanDecision.decision | normalize values | Apply does not necessarily mean high Fit |
| CSM/FA · Your notes | HumanDecision.reason | preserve raw | May be blank or contain multiple reasons |
