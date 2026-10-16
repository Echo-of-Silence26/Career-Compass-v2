# Evaluation Specification

Status: Draft v0.2
Owner: Echo-of-Silence26
Current objective: see `EXPERIMENTS.md` for the active and planned experiments.

## 1. Evaluation Question

Evaluation is organised into three levels:

1. **System quality:** does the AI execute the defined screening policy and
   produce a defensible fit label?
2. **Process efficiency:** does AI pre-assessment reduce human review effort?
3. **Market outcome:** under a standardized application protocol, do Strong and
   Plausible Fit applications produce interview opportunities, and do Fit labels
   separate groups with different interview outcomes?

Human agreement is not proof of market fit. System-human agreement evaluates
policy execution; interview outcomes evaluate whether the policy and market
positioning are useful.

## 2. Unit of Evaluation

- One job record
- One CandidateProfile version
- One Rubric/Policy version
- One model assessment result

## 3. Prediction Schema

- `hard_disqualifier_policy_version`
- `fit_policy_version`
- `hard_disqualifier_assessment`
- `capability_fit_label`: Strong Fit / Plausible Fit / Weak Fit / Unclear
- `skills` / `core_skills` / `industry` / `evidence` / `industry_evidence`:
  the skill map (Fit v0.3)
- `unknowns`
- `human_fit_label`: recorded independently during evaluation

The model must not produce Attractiveness, Apply, Review, or Skip.
The v1 `recommendation` and human application decision remain immutable
historical fields only; neither is Capability Fit ground truth.

### Human Application Decision

- Any hard-disqualifier `Fail` ends Fit assessment and remains in the exclusion
  audit.
- Every job with no `Fail` is stored, assigned a Fit label, and presented for
  human review.
- `Strong Fit`, `Plausible Fit`, `Weak Fit`, and `Unclear` do not cause or
  prevent an application. The human makes the final decision.

This boundary is outside the model and is not a prediction to be evaluated as
model intelligence.

### Versioned Decision Policies

Evaluation mechanics and decision policy are versioned separately. This file
defines how system performance is evaluated; track-specific policy files define
which jobs should proceed, be reviewed, or be excluded.

- Shared hard-disqualifier policy for all target role families:
  [`HARD_DISQUALIFIER_POLICY.md`](HARD_DISQUALIFIER_POLICY.md),
  version `hard-disqualifier-v0.2`
- Shared capability-fit policy for all target role families:
  [`CAPABILITY_FIT_POLICY.md`](CAPABILITY_FIT_POLICY.md),
  version `capability-fit-v0.3` (v0.2 archived)

Every assessment result must retain all policy versions used to produce it.
Historical results must not be silently relabeled when the policy changes.

## 4. Ground-Truth Policy

### Evidence and Interpretation Principles

- **The original job description takes precedence.** Extract all job
  requirements, responsibilities, language requirements, location constraints,
  experience requirements, and tool requirements primarily from the original
  job description.
- **Candidate evidence takes precedence when assessing capability coverage.**
  Assess whether the candidate meets a requirement only on the basis of the
  candidate's CV, projects, work history, or information explicitly provided by
  the user.
- **Keep facts and inferences separate.** A fact is directly supported by the
  source material—for example, the job description states that fluent German is
  required. An inference is a reasoned assumption—for example, a Germany-based
  CSM role may require German even when the job description does not say so.
  Inferences must be explicitly labeled and must not be presented as facts.
- **Mark uncertainty as a risk.** If the job description does not specify
  compensation, language requirements, visa sponsorship, or location
  flexibility, do not assume a favorable answer. Mark the item as `Risk` or
  `Unknown`, as appropriate.
- **Do not substitute aspiration for evidence.** Statements such as “I can
  learn it” may reduce perceived risk, but they do not demonstrate existing
  experience. Similarly, AI assistance may be treated as supplementary support,
  but it must not substitute for core experience unless the job description
  explicitly values AI capability.

Historical Apply/No behavior may help locate cases for review, but it cannot be
used directly as the new Fit reference label. The rerun requires an independent
human Fit judgment based on the original JD, the same Candidate Profile/CV
version, and the current Fit policy. Records without sufficient evidence are
marked `Unclear` or excluded from a specific comparison with the reason retained.

## 5. Dataset Partitions

- Development: used for analysis and iteration
- Test: frozen until final evaluation
- Challenge: boundary cases such as language, compensation, and transferable skills
- Excluded: insufficient data or label quality

## 6. Baselines

### v1 Baseline — CSM Only

The v1 baseline contains only the 88 CSM records with human feedback. It
compares the initial recommendation with the user's eventual Apply / Do not
apply label. The 15 non-CSM records from the broader 103-record historical audit
are outside the v1 evaluation scope and are not included in any v1 metric.

| | Actual positive: Apply | Actual negative: Do not apply | Total |
|---|---:|---:|---:|
| Predicted positive: recommended | TP = 16 | FP = 30 | 46 |
| Predicted negative: not recommended | FN = 13 | TN = 29 | 42 |
| Total | 29 | 59 | 88 |

- Precision: 34.78% (reported as 34.8%)
- Recall: 55.17% (reported as 55.2%)
- Accuracy: 51.14% (reported as 51.1%)
- Specificity: 49.15% (reported as 49.2%)

These are the fixed v1 baseline classification metrics within the 88 labeled
CSM records. They do not measure how completely the scraper captured relevant
jobs from all available market postings. No failure-mode conclusion has yet
been approved for this round; mismatch causes will be documented after the case
review.

The baseline is retained for historical comparison only. The current system no
longer predicts Apply, so its primary success criteria are not improvements to
the old Apply precision or recall.

### Retrospective Rerun Baseline

Use the same 88 CSM record IDs and preserve all original inputs and outputs.
Rerun each eligible record using the current Hard-Disqualifier and Capability
Fit policies, one fixed Candidate Profile/CV version, and one fixed prompt,
model, and parameter configuration. The rerun compares reasoning and labels,
not old recommendation agreement.

## 7. Metrics

### Metric Hierarchy

#### System Quality

- Fit-label agreement with independent human review
- Hard-disqualifier miss rate
- known-problem repair rate
- regression error rate on previously acceptable reasoning
- label-transition and error-category distribution, including transferability,
  central-responsibility, people-management, and title/keyword-match errors

#### Process Efficiency
- Human override rate
- Review workload or reduction

#### Market Outcome

- Interview invitation count
- Interview invitation rate
- Interview invitation count and rate grouped by Fit label
- Interview outcomes grouped by market positioning or role family

Capability Fit is a predictor, not an outcome. The next-round test
uses categorical labels rather than a numerical score. The hypothesis to test is
that Strong, Plausible, and Weak Fit produce meaningfully different interview
outcomes; the ordering must be learned from market results rather than assumed.

The normal market cohort uses one fixed role-family CV with a short,
fixed Summary, no cover letter, and no interest-driven application-material
changes. CV version and application-protocol version must be recorded.

### Classification Terms

For the current binary evaluation, positive means the user eventually marked
the job **Apply**, and predicted positive means the initial assessment
recommended the job. Therefore:

- **True positive (TP):** recommended, and the user marked Apply.
- **False positive (FP):** recommended, but the user marked Do not apply.
- **False negative (FN):** not recommended, but the user marked Apply.
- **True negative (TN):** not recommended, and the user marked Do not apply.

### Metric Definitions and Formulas

- **Precision** = `TP / (TP + FP)`. Of all jobs recommended by the initial
  assessment, the share the user eventually marked Apply. Current result:
  `16 / (16 + 30) = 34.78%`.
- **Recall (sensitivity)** = `TP / (TP + FN)`. Of all jobs in the labeled pool
  that the user eventually marked Apply, the share the initial assessment
  recommended. Current result: `16 / (16 + 13) = 55.17%`.
- **Accuracy** = `(TP + TN) / (TP + FP + FN + TN)`. The share of all evaluated
  jobs for which the initial recommendation agreed with the eventual label.
  Current result: `(16 + 29) / 88 = 51.14%`.
- **Specificity (true-negative rate)** = `TN / (TN + FP)`. Of all jobs in the
  labeled pool that the user eventually marked Do not apply, the share the
  initial assessment did not recommend. Current result:
  `29 / (29 + 30) = 49.15%`.

### What These Metrics Measure

These metrics describe the same binary classifier from different reference
groups. The denominator shows the question each metric answers:

| Metric | Reference group (denominator) | Question answered | Error exposed when low |
|---|---|---|---|
| Precision | All predicted positives (`TP + FP`) | When the system says “positive,” how often is it right? | Too many false positives |
| Recall / sensitivity | All actual positives (`TP + FN`) | Of the positives that truly exist, how many did the system find? | Too many false negatives |
| Specificity | All actual negatives (`TN + FP`) | Of the negatives that truly exist, how many did the system correctly reject? | Too many false positives |
| Accuracy | All evaluated examples | What share of all decisions was correct? | Overall error, without distinguishing its type |

In plain language, **precision measures the trustworthiness or purity of
positive predictions**, while **recall measures their coverage**. Specificity
is recall's negative-class counterpart: recall asks whether actual positives
were found, whereas specificity asks whether actual negatives were correctly
excluded. Accuracy gives the overall hit rate across both classes.

No single metric is sufficient because false positives and false negatives can
have different costs. Lowering a decision threshold usually finds more actual
positives and raises recall, but it may also create more false positives and
lower precision and specificity. Raising the threshold commonly produces the
opposite trade-off.

Accuracy also needs special care when the classes are imbalanced. If only 10
of 1,000 examples are positive, a classifier that always predicts negative has
99% accuracy but 0% recall. It is therefore possible for high accuracy to hide
complete failure on a rare but important positive class.

A compact way to remember the four perspectives is:

- **Precision:** how correct are the positives we predicted?
- **Recall:** how many of the actual positives did we find?
- **Specificity:** how many of the actual negatives did we exclude?
- **Accuracy:** how many decisions were correct overall?

Recall here is **recommendation recall within the labeled pool**. It is not
scraping recall or market-wide coverage. Market-wide coverage would require a
known or reliably estimated set of all relevant available postings, including
relevant postings the scraper did not collect. That denominator is currently
unknown, so market-wide scraping recall cannot be calculated.

The actual label is also a behavioral label: it records the user's eventual
application decision. It should not be interpreted as proof that a job
objectively met every criterion, was a good overall fit, or would lead to a
successful application.

### Retrospective Rerun Measures

- **Known-problem repair rate:** known v1 problem cases no longer exhibiting the
  same supported failure mode / all rerunnable known problem cases in scope.
- **Regression error rate:** sampled previously acceptable cases that acquire a
  new material policy or reasoning error / all previously acceptable cases
  reviewed.
- **Human Fit agreement:** exact agreement between AI and independent human
  Strong/Plausible/Weak/Unclear labels. Also report adjacent versus material
  disagreements; do not convert the labels into hidden numeric scores.
- **Hard-disqualifier miss rate:** explicit current-policy Fail cases missed by
  the rerun / all explicit Fail cases in the reviewed reference set.
- **Transition matrix:** historical recommendation and reason versus new hard-
  disqualifier state and Fit label. This is diagnostic, not an accuracy matrix.
- **Unclear/exclusion rate:** records that cannot support a reliable judgment,
  with missing-evidence reasons.

### Product Value

- Review workload or reduction
- Human override rate
- Good-job miss proxy

### Reliability

- Structured-output success rate
- Run-completion rate
- Latency
- Cost

## 8. Error Taxonomy

Use a three-level analysis to keep the
observed error category, inferred failure mode, and root-cause ownership
separate. FP and FN are evaluation outcomes and must not be used as substitutes
for any of these three fields.

- Missing or unexecuted hard rule
- Fit mismatch: central responsibility, people management, ownership/scope, or seniority
- Transferability miss
- Title/keyword overmatch
- Data-quality problem
- Insufficient reason or uncertain label
- System-execution failure

## 9. Experiment Rules

- Use a fixed data version for each experiment
- Change one primary variable at a time, or explicitly document interactions
- Save Prompt, Rubric, Policy, model, and parameter versions
- Write the hypothesis before running the experiment
- Report grouped errors as well as aggregate metrics
- Check recall or coverage proxy whenever precision improves
- Keep the test set frozen until final selection
- Evaluate known bad cases for repair, and separately inspect previously
  acceptable cases for regression. A fixed 88-record rerun is retrospective
  development evidence and must not be presented as unseen generalization.

## 10. Known Limitations

- Application behavior is not the same as objective job fit
- Preferences and job-search policy change over time
- Historical data reflects an older CSM/FA strategy and may differ from the current AI PM target
- True market coverage cannot be measured without a complete set of available jobs
