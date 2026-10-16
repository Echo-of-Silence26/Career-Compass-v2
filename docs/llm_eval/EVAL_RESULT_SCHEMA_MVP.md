# Evaluation Result Schema MVP

Status: Active
Schema version: `eval-result-v0.2`
Change from v0.1: `capability_fit` now carries the three-layer shape of
`capability-fit-v0.3` (`skills`, `core_skills`, `industry`, five-state
`evidence`, `industry_evidence`) in place of
`core_matches` / `key_gap`. Records written under v0.1 are retained as-is and
are not re-parsed against this version.
Scope: one prospective MVP evaluation result per canonical Job

## 1. Purpose

This document owns the final structured result produced by the MVP
evaluation pipeline. Policy documents define how judgments are made; this
schema defines how those judgments are represented, validated, and persisted.

The result contains no Attractiveness score, numeric Fit score, or Apply / Do
not apply recommendation. Human review and the human application decision are
separate records and must not overwrite the model result.

The draft Industry Feasibility policy is not part of the current MVP execution
flow or this schema.

## 2. Canonical Result

```yaml
EvaluationResult:
  evaluation_id: string
  job_id: string
  run_id: string

  company: string
  title: string
  source_url: string
  job_content_hash: string
  candidate_profile_version: string

  input_status: Eligible | Blocked
  blocking_reasons: string[]

  hard_disqualifier:
    policy_version: string|null
    rules:
      - rule_id: string
        rule_name: string
        state: Pass | Fail | Unknown | Flag
        evidence_quote: string|null
        candidate_evidence: string|null
        reason: string
    overall_decision: Exclude | ProceedToCapabilityFit | null

  capability_fit:
    policy_version: string|null
    label: StrongFit | PlausibleFit | WeakFit | Unclear | null
    skills:                       # Layer 1, CV-blind
      - skill_id: string
        skill: string
        category: tool | method | language | credential
        jd_signal: required | preferred | responsibility
        jd_quote: string
    core_skills:                  # Layer 2, CV-blind; exactly min(3, len(skills)), most central first
      - skill_id: string
        reason: string
    industry:                     # parallel variable, CV-blind; null only for a null label
      industry: string|null
      jd_signal: required | preferred | context_only
      jd_quote: string|null
    evidence:                     # Layer 3, core-blind; one per skill
      - skill_id: string
        state: done | participated | adjacent | unconfirmed | not_done
        candidate_evidence: string|null
        scope: string|null
        shifted_dimensions: (object | customer | goal | product_context | delivery_model | tool | depth)[]
        reasoning: string         # required for every state
    industry_evidence:            # same fields as an evidence entry, without skill_id
      state: ...
    unknowns: string[]

  fit_skip_reason: HardDisqualifierFail | null

  evaluation_status: Completed | Blocked | Failed
  failure_stage: HardDisqualifier | CapabilityFit | null
  failure_reason: string|null

  prompt_version: string
  model_identifier: string
  model_config_version: string
  output_schema_version: string
  evaluated_at: datetime
```

## 3. Field Rules

### 3.1 Identity and Versions

- `evaluation_id` uniquely identifies this assessment result.
- `job_id` references one canonical, deduplicated Job.
- `run_id` identifies the prospective MVP execution run.
- `job_content_hash` identifies the captured JD snapshot used for evaluation.
- `candidate_profile_version` identifies the fixed candidate evidence used by
  both assessment stages.
- `prompt_version`, `model_identifier`, `model_config_version`, and
  `output_schema_version` are required
  for every result, including `Blocked` and `Failed` results.
- `output_schema_version` must be `eval-result-v0.2` for records
  conforming to this document.

### 3.2 Input Status

- `Eligible`: the extracted JSON is parseable and all required assessment
  inputs are present.
- `Blocked`: core evidence or execution context is missing, mismatched, failed,
  or unreliable, so assessment would require guessing. Record at least one
  `blocking_reasons` entry and send the record to human review without an LLM
  assessment call.

For `Eligible`, `blocking_reasons` is empty. For `Blocked`, it is non-empty.
Undisclosed optional facts are represented by the applicable
Hard-Disqualifier `Unknown` / `Flag` or Capability-Fit `unknowns`, not by a
third pre-assessment input state.

### 3.3 Hard Disqualifier

- Evaluate every rule in the active Hard-Disqualifier policy for an eligible
  input.
- Store one object per rule in `rules`; do not combine multiple rules into one
  string.
- `rule_id` uses the policy identifier, for example `3.1(b)`.
- `evidence_quote` contains the shortest sufficient JD evidence. It is required
  for every `Fail`, `Unknown`, or `Flag`; it may be null for `Pass` when no
  specific quotation is necessary.
- `candidate_evidence` is required when the rule depends on a comparison with
  known candidate capability; otherwise it may be null.
- Any `Fail` produces `overall_decision: Exclude`.
- No `Fail` produces `overall_decision: ProceedToCapabilityFit`.
- `Unknown` and `Flag` do not automatically exclude the job.

There is no separate `triggering_rules` field. Excluding rules are derived from
the entries in `rules` whose `state` is `Fail`. This avoids duplicating data and
prevents disagreement between a summary field and the underlying rule results.

### 3.4 Capability Fit

- Run Capability Fit only when the Hard-Disqualifier overall decision is
  `ProceedToCapabilityFit`.
- `label` uses exactly one of `StrongFit`, `PlausibleFit`, `WeakFit`, or
  `Unclear`, and must equal the policy §8 aggregation of the core skills'
  evidence states. It is derived by code, not chosen by the model. Neither
  non-core skills nor the industry affect it.
- `skill_id` values in `skills` are unique. `core_skills` names exactly
  `min(3, len(skills))` distinct Layer 1 skills. `evidence` contains exactly
  one entry per `skills` entry, with none missing, extra, or duplicated.
- Evidence field rules, which apply to both `evidence` and
  `industry_evidence`:
  - `candidate_evidence` is null for `unconfirmed` and required for every
    other state. For `not_done` it cites the explicit profile statement.
  - `scope` is required for `done` and `participated`, and null otherwise.
  - `shifted_dimensions` is non-empty for `adjacent`, and empty otherwise.
  - `reasoning` is required for every state. It explains the assigned state:
    what the evidence establishes and what it does not; for `adjacent` what
    transfers; for `unconfirmed` what to confirm. The review export prints a
    fixed verdict per state in front of it (Fit policy §9.1).
- `industry_evidence` is present exactly when `industry.industry` is non-null.
- Gaps (`not_done`) and pending confirmations (`unconfirmed`) are read from
  `evidence`, not stored separately.
- `unknowns` contains only missing JD information that could materially
  change a state or the core marking; use an empty array when there is none.
- A Fit result with a null label carries empty `skills`, `core_skills`, and
  `evidence`, and null `industry` / `industry_evidence`.

### 3.5 Minimal Execution Status

The MVP uses one top-level execution status instead of a separate state machine
for every stage:

- `Completed`: the applicable policy path completed normally. A Hard-
  Disqualifier `Exclude` with skipped Capability Fit is still `Completed`.
- `Blocked`: the input guard stopped evaluation before any assessment call.
- `Failed`: an attempted Hard-Disqualifier or Capability-Fit call failed or
  returned invalid output.

For `Failed`, both `failure_stage` and `failure_reason` are required. Otherwise
they are null. The MVP records the failure for human review and performs no
automatic retry or repair.

## 4. Cross-Field Validation Rules

1. `input_status: Blocked` requires `evaluation_status: Blocked`, non-empty
   `blocking_reasons`, empty Hard-Disqualifier rules, null policy decisions and
   Fit label, null `fit_skip_reason`, and null failure fields.
2. `input_status: Eligible` permits evaluation to start and requires the active
   Hard-Disqualifier policy version.
3. Any Hard-Disqualifier `Fail` requires `overall_decision: Exclude`, null
   Capability-Fit policy/label, and `fit_skip_reason: HardDisqualifierFail`. A
   valid exclusion result has `evaluation_status: Completed`.
4. No Hard-Disqualifier `Fail` requires
   `overall_decision: ProceedToCapabilityFit`.
5. A successfully completed `ProceedToCapabilityFit` result requires the active
   Capability-Fit policy version, exactly one Fit label, and null
   `fit_skip_reason`.
6. `evaluation_status: Failed` requires non-null `failure_stage` and non-empty
   `failure_reason`; it must not contain a fabricated result for the failed
   stage.
7. The result must not contain Attractiveness, Apply recommendation, Review,
   Skip, or numeric Fit fields.

## 5. Examples

### 5.1 Hard-Disqualifier Fail

```yaml
input_status: Eligible
blocking_reasons: []

hard_disqualifier:
  policy_version: hard-disqualifier-v0.2
  rules:
    - rule_id: "3.1(b)"
      rule_name: senior_years
      state: Fail
      evidence_quote: "5+ years' experience in Customer Success"
      candidate_evidence: null
      reason: The explicit minimum experience requirement is at least five years.
  overall_decision: Exclude

capability_fit:
  policy_version: null
  label: null
  skills: []
  core_skills: []
  industry: null
  evidence: []
  industry_evidence: null
  unknowns: []

fit_skip_reason: HardDisqualifierFail
evaluation_status: Completed
failure_stage: null
failure_reason: null
```

### 5.2 Proceed with a Flag

```yaml
input_status: Eligible
blocking_reasons: []

hard_disqualifier:
  policy_version: hard-disqualifier-v0.2
  rules:
    - rule_id: "3.1(b)"
      rule_name: senior_years
      state: Flag
      evidence_quote: "Extensive experience in customer success"
      candidate_evidence: null
      reason: Seniority wording is material but does not state an explicit year floor.
  overall_decision: ProceedToCapabilityFit

capability_fit:
  policy_version: capability-fit-v0.3
  label: PlausibleFit
  skills:
    - skill_id: S1
      skill: B2B client account management
      category: method
      jd_signal: required
      jd_quote: "Act as the main point of contact for our B2B clients"
    - skill_id: S2
      skill: Customer onboarding programme design
      category: method
      jd_signal: responsibility
      jd_quote: "Design and run onboarding for new customers"
    - skill_id: S3
      skill: Customer health monitoring and churn prevention
      category: method
      jd_signal: required
      jd_quote: "Monitor account health and prevent churn"
    - skill_id: S4
      skill: CRM platform
      category: tool
      jd_signal: preferred
      jd_quote: "Salesforce or similar CRM is a plus"
  core_skills:
    - skill_id: S1
      reason: Client ownership is the central function of the role.
    - skill_id: S3
      reason: Retention is the role's main success metric.
    - skill_id: S2
      reason: Onboarding is a primary listed responsibility.
  industry:
    industry: HR software (B2B SaaS)
    jd_signal: preferred
    jd_quote: "Experience in HR tech is a plus"
  evidence:
    - skill_id: S1
      state: done
      candidate_evidence: "ev-01: primary point of contact for two pharma B2B accounts"
      scope: Owned the two named accounts end-to-end.
      shifted_dimensions: []
      reasoning: Owned renewal-critical B2B accounts; covers the skill as worded.
    - skill_id: S2
      state: adjacent
      candidate_evidence: "ev-01: owned launch of two new drug companion programmes"
      scope: null
      shifted_dimensions: [object]
      reasoning: Structured launch/onboarding transfers; partner programmes, not software users.
    - skill_id: S3
      state: participated
      candidate_evidence: "ev-01: monitored performance against KPIs"
      scope: Monitored programme KPIs; no ownership of a churn-prevention process.
      shifted_dimensions: []
      reasoning: Tracked programme KPIs; did not own a churn-prevention process.
    - skill_id: S4
      state: unconfirmed
      candidate_evidence: null
      scope: null
      shifted_dimensions: []
      reasoning: The CV does not show hands-on Salesforce or other CRM use. Have you used one?
  industry_evidence:
    state: adjacent
    candidate_evidence: "ev-01: B2B SaaS health app"
    scope: null
    shifted_dimensions: [product_context]
    reasoning: B2B SaaS transfers; healthcare, not HR tech.
  unknowns: []

fit_skip_reason: null
evaluation_status: Completed
failure_stage: null
failure_reason: null
```

## 6. Storage and Human Review

- Persist one result per `evaluation_id` in the run's append-only JSONL output.
- Never overwrite a historical result when the Job, Candidate Profile, policy,
  prompt, model, or schema version changes; create a new result.
- Preserve `Blocked`, `Failed`, `Unknown`, `Flag`, and `Exclude` records in run
  totals.
- Human review may reference and correct a model result, but must not mutate the
  original `EvaluationResult`.
