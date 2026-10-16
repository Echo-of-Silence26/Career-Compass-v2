# Experiment Log

## EXP-001 — Retrospective Policy Rerun on the v1 CSM Dataset

- Date: 2026-08-10
- Status: Defined; input reconstruction in progress
- Hypothesis: Separating explicit Hard Disqualifiers from four-level Capability
  Fit, and removing Attractiveness and Apply prediction, will repair known v1
  policy and Fit failures without introducing material regressions in cases
  whose prior reasoning was acceptable.
- Fixed dataset: the same 88 CSM record IDs used by the v1 baseline. Preserve
  original inputs, recommendation, human action, and reasons. A record may be
  excluded from a specific comparison if its original JD or candidate evidence
  is insufficient, but its ID and exclusion reason remain in the audit.
- Baseline: v1 historical recommendation baseline: TP 16, FP 30, FN 13, TN 29.
  These Apply metrics provide historical context only and are not the new target.
- Change:
  1. run `hard-disqualifier-v0.1`;
  2. run `capability-fit-v0.1` when no rule returns Fail;
  3. output no Attractiveness or Apply recommendation;
  4. compare the result with an independent human policy/Fit review.
- Controlled configuration: one Candidate Profile/CV version, prompt version,
  model, parameters, and source snapshot for all records.
- Primary measures: known-problem repair rate; regression error rate; exact
  human Fit-label agreement; hard-disqualifier miss rate; Unclear/exclusion rate.
- Diagnostic outputs: per-record old-to-new transition; counts by previous
  FP/FN/TP/TN group; error category; failure mode; root-cause owner; and Fit label.
- Repair review set: all rerunnable known v1 mismatch cases, initially the 30 FP
  and 13 FN records, after separating label-design disagreements from supported
  system failures.
- Regression review set: all available former TP and TN records, or a declared
  sample selected before inspecting new results if full review is infeasible.
- Generalization claim: none. Because the same data informed the new policies,
  this experiment measures repair and regression only. A frozen unseen sample
  is required later.
- Results (blind run `exp-001-blind-rerun`, 2026-08-11, claude-sonnet-5): run
  on 119 job IDs from the regression master file rather than only the 88 CSM
  records; 106 job descriptions were retrievable, 13 were not. Hard
  Disqualifier v0.1 excluded 45 (mostly language and field/travel rules) and
  passed 61. Capability Fit v0.1 on the 61: 1 Strong, 40 Plausible, 20 Weak;
  re-scored under Fit v0.2, 13 of 61 labels changed (mostly Plausible → Weak).
  Human review columns for exclusions and Fit labels were not filled in, so
  agreement with human judgment is not yet measured.
- Decision: Pending — Keep / Revert / Iterate. The passed set became the fixed
  dataset for EXP-002.
- Readiness audit: The 88-record audit workbook contains company, title,
  historical score/reason, human action/reason, and FP/FN/TP/TN class, but not
  the original JD text required by the current evidence policy. Historical
  `verbatim.json` and `outputs_scrape/scraped.json` retain responsibility and
  qualification text for only a subset of companies. EXP-001 must first join
  recoverable JD text to the fixed record IDs and report coverage; derived
  historical rationales must not be substituted for original JDs.

## EXP-002 — Hard-Disqualifier v0.2 Rerun on the Previously-Passed Blind Set

- Date: 2026-08-12
- Hypothesis: Adding explicit seniority-band hard disqualifiers (5+ year floor;
  people-management mandate) will exclude decidable over-band roles at screening
  without removing negotiable roles, which instead surface as `Flag`.
- Fixed dataset: the 61 jobs in `Review_Passed` of
  the EXP-001 blind-run workbook, kept private (jobs that
  passed hard-disqualifier v0.1 in EXP-001). Only links that opened were scored;
  no link was broken/blank in this run.
- Baseline: EXP-001 screening under `hard-disqualifier-v0.1` — all 61
  Proceed to fit.
- Change: apply `hard-disqualifier-v0.2` rules 3.1(b) and 3.1(c) to
  each job by fetching its job description and extracting explicit minimum-years
  and team-leadership wording. Fit labels unchanged.
- Model and parameters: claude-sonnet-5; run_id `exp-002-hd-v2-rerun`; JD text
  fetched live from each stored posting URL.
- Prompt/Rubric/Policy versions: `hard-disqualifier-v0.2`
  (fit policy untouched, `capability-fit-v0.2`).
- Metrics / Results: of 61 previously-passed jobs — **12 now Exclude** (9 on the
  5+ year rule, 6 on the people-management rule, 3 on both), **15 now Flag**
  (3–5 year band or ambiguous no-number wording; retained for human review),
  **34 still Pass**. Recall-impact log = the 12 excluded job_ids
  (8, 10, 15, 22, 45, 49, 71, 76, 80, 101, 105, 111).
- Data-quality note: the blind workbook's stored hyperlinks for job_ids
  14/15/16/22 were rotated (a 4-cycle); all 61 were recovered by matching the
  fetched company to the stored job. Job 107 has a JD/title mismatch
  (title = CSM, body = Purchasing Manager) and is flagged for human review.
- Output: the EXP-002 rerun workbook, kept private
  (tabs: Summary, HD_Change_v2_v3 delta, HD_v2_Rerun, Newly_Failed,
  Link_Scramble_Log, Run_Metadata).
- Error analysis: exclusions are driven by explicit JD wording quoted per case;
  the 15 `Flag` cases are deliberately left for human review rather than
  auto-excluded, per the accepted decision.
- Decision: Keep — accepted as ADR-012; policy status set to Accepted.
- Next step: when a frozen unseen job sample is available, measure whether the
  v0.2 gates generalize and quantify the recall cost from the logged exclusions.

## EXP-003 — Prospective Collection Under Frozen v0.2 Policies

- Date defined: 2026-08-14
- Status: Ready for collection; batch not yet created.
- Purpose: test whether the accepted Hard-Disqualifier changes generalise to a
  new time-separated job batch while observing, rather than tuning, Capability
  Fit v0.2.
- Fixed policies: `hard-disqualifier-v0.2` and
  `capability-fit-v0.2`, frozen by ADR-013.
- Population: newly collected jobs not used to create or tune
  either v0.2 policy. Store collection source, query, timestamp, source ID/URL,
  resolved URL, and immutable raw JD evidence.
- Pipeline rule: any Hard Disqualifier `Fail` is excluded from Fit assessment
  but retained in the run audit. Every non-failed job is stored in the database,
  remains human-visible, receives a Fit label, and is left to the human reviewer
  for the final application decision regardless of label.
- Controls: do not change either policy during the run; deduplicate before final
  batch analysis; flag inaccessible, mismatched, expired, or incomplete JDs;
  preserve all exclusions with the triggering rule and quoted evidence.
- Primary measures: collection count and data-quality status; HD Fail/Flag/Pass
  distribution; human agreement/override on HD; number and reasons for v0.2
  exclusions that the reviewer would retain.
- Diagnostic Fit measures: Strong/Plausible/Weak/Unclear distribution, human
  overrides, review time, and the share of Weak jobs still judged worth pursuing.
  These diagnose usefulness and calibration; they do not make Fit an ingestion
  or visibility gate.
- Decision after run: keep frozen v0.2, propose a separately versioned change,
  or design a controlled follow-up experiment. Never rewrite EXP-003 results
  using a policy learned from the same batch.

## EXP-004 — Narrowed Sourcing Measured by Interview Invitation Rate

- Date defined: 2026-10-16
- Status: Proposed.
- Hypothesis: narrowing sourcing to two target role families, with sourcing and
  Hard Disqualifier screening fully automated, raises the interview invitation
  rate without increasing human review time.
- Changes: sourcing policy v0.3 (two role families, each collected job tagged
  with its family); add a post-application outcome (`No reply` / `Rejected` /
  `Invited`) to `HumanDecision`, linked to the job ID.
- Primary measures: invitation rate per role family; qualifying postings per
  week; human review time per week.
- Controls: no policy or rubric changes during the measurement window.
- Results: Pending.
- Decision: Pending — Keep / Revert / Iterate.

## Experiment Template

### EXP-NNN — Title

- Date:
- Hypothesis:
- Fixed dataset:
- Baseline:
- Change:
- Model and parameters:
- Prompt/Rubric/Policy versions:
- Metrics:
- Results:
- Error analysis:
- Decision: Keep / Revert / Iterate
- Next step:

## Recommended Metrics

- Human agreement for four-class categorical Fit
- Known-problem repair rate and regression error rate
- Hard-disqualifier miss rate
- Structured-output success rate
- Per-job latency and cost
- Human override rate
- Number of unsupported statements
