# MVP Evaluation Execution Prompt

Status: Active
Version: `eval-execution-v0.2` (v0.2: Stage B split into
decomposition and matching calls for Capability Fit v0.3)
Experiment scope: EXP-003 prospective MVP run

Purpose: define the model instructions used by the prospective MVP
evaluation pipeline. This document applies to newly collected job records. It
does not ask the evaluator to reconstruct a historical prompt or reproduce a
historical decision.

The retired 11.08 workbook blind-run prompt is archived outside this repository.

## 1. Execution Context

The orchestrator turns the per-record instructions below into programmatic
model calls. Do not paste this prompt into a conversation to run an entire
workbook, and do not fetch a live job page during evaluation.

For every prospective run, the orchestrator fixes and records:

- `run_id`;
- Candidate Profile/CV version;
- prompt version and content hash;
- Hard-Disqualifier policy version;
- Capability-Fit policy version;
- model and model-configuration identifier;
- output-schema version; and
- sourcing-config version or content hash.

The MVP uses the JD snapshot captured in the current sourcing run. The source
URL provides provenance but is not a substitute for captured JD evidence.

## 2. Required Inputs per Job

The evaluation input contains:

1. one canonical, deduplicated `Job` record with stable identity and source
   provenance;
2. its immutable raw JD snapshot or reference and content hash;
3. the fixed Candidate Profile/CV;
4. the frozen `hard-disqualifier-v0.2` policy;
5. the `capability-fit-v0.3` policy (frozen before the run starts); and
6. all execution versions listed in §1.

Before any model call, the deterministic Assessment Eligibility guard defined
in `DATA_PIPELINE_MVP_SPEC.md` §4.2.1 must return `Eligible`. A `Blocked` job is
not sent to either evaluator. The pipeline records its `blocking_reasons` and
flag for human review. Missing optional facts disclosed
by neither source nor candidate are not pipeline failures; the applicable
policy decides whether they produce `Pass`, `Unknown`, or `Flag`.

## 3. Isolation and Evidence Rules

- Evaluate only the supplied Job/JD snapshot, Candidate Profile, and frozen
  policies.
- Do not read or use historical assessments, old Fit scores, recommendations,
  application decisions, user decisions, outcomes, or mismatch analyses.
- Do not infer the expected result from earlier runs or edit a result to match
  historical behaviour.
- Do not infer missing JD facts from the title, company reputation, or generic
  knowledge of similar roles.
- Keep facts and inferences separate. Every decision must cite short, specific
  JD evidence and, where relevant, Candidate Profile evidence.
- Do not modify or reinterpret a policy during the run. Record a possible
  policy improvement separately for a future version.
- Do not output an `Apply`, `Do not apply`, `Review`, `Skip`, Attractiveness, or
  numeric Fit prediction.

This is a prospective frozen-policy evaluation, not an exercise in guessing
how an earlier prompt was written.

## 4. Stage A — Hard Disqualifier

Run this stage for every `Eligible` job.

```text
Apply every rule in the supplied Hard-Disqualifier policy to the
supplied Job/JD snapshot and fixed Candidate Profile.

Return only policy-defined rule states and the policy-defined overall decision.
For each rule, provide a concise reason and short quoted evidence from the JD
and, when relevant, the Candidate Profile. Do not use Capability Fit to offset
a Hard-Disqualifier Fail. Do not turn absent optional information into an
inferred Fail.
```

If any rule returns a confirmed `Fail`, persist the Hard-Disqualifier result,
retain the job in the exclusion audit, and skip Stage B. Otherwise proceed to
Stage B, including when the policy returns a reviewable `Unknown` or `Flag`.

At minimum persist:

- `job_id`, `company`, `title`, `source_url`;
- assessment eligibility state and version;
- Hard-Disqualifier policy version;
- every rule state, reason, and evidence;
- overall Hard-Disqualifier decision;
- `evaluated_at`, `run_id`, model/configuration, prompt, and schema versions.

## 5. Stage B — Capability Fit

Run this stage only when Stage A has no confirmed `Fail`. Stage B follows the
three-layer structure of the Capability-Fit policy and makes two model calls.
The label is derived afterwards by code (policy §8).

**B1: Decomposition (Layers 1–2 and industry).** The input is the Job/JD
snapshot only. The Candidate Profile is deliberately not supplied.

```text
Apply Layers 1 and 2 and the industry variable of the supplied
Capability-Fit policy to the Job/JD snapshot. First list every hard skill the
job requires, prefers, or clearly depends on, with a short JD quote for each.
Then mark the three most central skills with a short reason. Record the
industry separately, never as a skill. Do not assess any candidate, and do not
drop a skill because it seems minor.
```

**B2: Evidence matching (Layer 3).** The input is the Job/JD snapshot, the
fixed Candidate Profile, the complete B1 skill list, and the industry. The core
marking is deliberately withheld.

```text
Apply Layer 3 of the supplied Capability-Fit policy. For every
listed skill, and for the industry, assign one of done, participated,
adjacent, unconfirmed, or not_done using only Candidate Profile evidence. A
skill the profile does not mention is unconfirmed, never not_done. Cite the
evidence with its employer/project and result, record the candidate's
responsibility scope for done/participated, and give every entry a reasoning:
what the evidence establishes and what it does not, what transfers for
adjacent, and what to confirm for unconfirmed. Return one entry per skill
without skipping any, plus missing-JD unknowns. Do not choose a Fit label or
verdict wording, make an application recommendation, or use a numeric score.
```

At minimum persist:

- Capability-Fit policy version and the derived label;
- `skills` (Layer 1), `core_skills` (Layer 2), `industry`, `evidence`, and
  `industry_evidence` (Layer 3) as separate fields;
- `unknowns`; and
- `evaluated_at`, `run_id`, model/configuration, prompt, and schema versions.

A failure in either call fails the whole stage. No partial Fit result is
persisted.

All four Fit labels remain visible for human review. Capability Fit neither
causes nor prevents an application.

## 6. Persistence, Validation, and Review

- Append results to the run's JSONL records and unified run output; never
  overwrite a historical run.
- Validate each stage's output independently. Retry or flag invalid model
  output without silently manufacturing missing fields.
- Preserve every Hard-Disqualifier exclusion with its triggering rule and
  quoted evidence for recall-impact review.
- Preserve `Blocked`, failed, partial, retried, and human-review-needed records;
  do not remove them from denominators.
- Use a small initial manual checkpoint to verify extraction quality, schema,
  evidence grounding, and policy execution before continuing the run. This is
  a quality-control checkpoint, not permission to tune the frozen policies.
- At run completion, verify unique job coverage and report counts for at least:
  `Eligible`, `Blocked`, Hard-Disqualifier overall states, Capability-Fit
  labels, model-call failures/retries, and human-review-needed records.

Any later comparison with human labels, overrides, application decisions, or
market outcomes occurs only after the model outputs are persisted and frozen.
Those comparisons evaluate different questions and do not redefine the
Capability-Fit ground truth retroactively.
