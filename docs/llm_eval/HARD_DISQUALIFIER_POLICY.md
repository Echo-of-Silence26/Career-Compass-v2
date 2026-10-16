# Hard-Disqualifier Policy

Policy version: `hard-disqualifier-v0.2`
Status: Frozen for next-round prospective test (2026-08-14)
Decision stage: Hard-disqualifier screening

## 1. Purpose

This policy defines the shared first-stage exclusions for all target role families. It is
intentionally narrow: only explicit, high-confidence conflicts should remove a
job before role-specific fit assessment.

The policy does not assess attractiveness. A job that passes this stage moves
to the relevant role-family fit assessment even when its industry, product, or
mission is not personally attractive.

## 2. Output States

Evaluate each rule as:

- `Pass`: the available evidence does not trigger the disqualifier.
- `Fail`: the job explicitly triggers the disqualifier.
- `Unknown`: the job does not provide enough information for a reliable decision.
- `Flag`: the wording is ambiguous and deserves attention during fit review, but
  must not cause automatic exclusion.

Overall decision:

- Any `Fail` -> `Exclude`.
- No `Fail` -> `Proceed to role-family fit assessment`.
- `Unknown` and `Flag` do not cause automatic exclusion.

## 3. Hard Disqualifiers

### 3.1 Career stage / seniority band mismatch

The candidate targets a mid-level individual-contributor band. A role is excluded
when its career stage falls clearly **outside that band on either side** — too
junior (entry programmes) or too senior (a high year floor or a people-management
mandate). Moderate, debatable differences inside the band do not disqualify.

**(a) Below band — entry programmes.** Return `Fail` when the role is explicitly:

- Internship
- Working Student / Werkstudent
- Trainee / Training Programme
- Graduate Programme

Part-time work is acceptable and must not be excluded on this basis.

**(b) Above band — explicit senior experience-year requirement.** Anchored on the
**minimum required years** stated for the core role, not on preferred or
"nice to have" years:

- Minimum required years **>= 5** -> `Fail` (significant, non-closable gap; skip
  fit assessment)
- Minimum required years **>= 3 and < 5** -> `Flag`, then proceed (mid-senior;
  keep for human review, do not auto-exclude)
- Minimum required years **< 3** -> `Pass`
- No explicit number stated, or the years apply only to a preferred/"plus"
  qualification -> `Unknown` (do not infer a floor)

Only an explicit stated number triggers a `Fail`. Ambiguous seniority wording
with no number — such as `senior`, `several years`, `proven track record`,
`extensive experience` — returns `Flag`, not `Fail`. When a range is given
(e.g. `5-7 years`), use the lower bound as the minimum required.

**(c) Above band — explicit people-management / team-leadership mandate.** Return
`Fail` when the job description explicitly assigns responsibility for a team in
**any** of the following forms, and the candidate has no people-management
evidence (direct or transferable):

- **Managing / leading a team** — owning direct reports or headcount (not merely
  coordinating a project);
- **Building / setting up a team** — hiring, recruiting, or standing up a new
  team or function;
- **Developing a team** — coaching, growing, or performance-managing reports.

Do not trigger on individual-contributor leadership wording such as `mentor`,
`lead initiatives`, `lead projects`, `thought leadership`, or `lead by example`.
Ambiguous wording that could mean either people management or IC influence
returns `Flag`, then proceeds.

The model must quote the job-description wording for any `Fail` or `Flag` under
(b) or (c) and must not infer an unstated year floor or management mandate.

**Recall-impact logging.** Because parts (b) and (c) are new and
non-compensatory, every job they exclude must be logged with its `job_id`, the
triggering part, and the quoted job-description evidence, so the recall cost
(potentially negotiable roles that were removed) can be reviewed later.

### 3.2 Compensation

The threshold is EUR 50,000 gross annual compensation. When a range is
published, use the **upper bound**, not the lower bound.

- Range upper bound >= EUR 50,000 -> `Pass`
- Range upper bound < EUR 50,000 -> `Fail`
- Single stated amount >= EUR 50,000 -> `Pass`
- Single stated amount < EUR 50,000 -> `Fail`
- Not disclosed, described only as competitive, or not reliably convertible ->
  `Unknown`

Examples:

| Published compensation | Result |
|---|---|
| EUR 45k-EUR 55k | Pass |
| EUR 50k-EUR 65k | Pass |
| EUR 40k-EUR 49k | Fail |
| Competitive | Unknown |
| Not disclosed | Unknown |

When the posting gives only OTE, variable compensation, hourly pay, another
currency, or an unclear mixture of base and variable pay, record the published
evidence and return `Unknown` unless it can be converted reliably under an
explicit evaluation convention.

### 3.3 Contract type

Return `Fail` when the employment itself is explicitly:

- Agency contract
- Maternity or parental-leave replacement
- Fixed-term contract
- Temporary contract

A job advertised by a recruitment agency is not automatically an agency
contract. The exclusion applies to the employment arrangement, not the channel
through which the vacancy was found.

### 3.4 Mandatory language requirements

Return `Fail` only when both conditions are satisfied:

1. The language requirement is explicitly mandatory, using wording such as
   `mandatory`, `required`, `essential`, `must have`, or an explicit required
   level such as native/C1/C2; and
2. The required level is known to exceed the candidate's recorded language
   capability.

Do not automatically exclude a role based on ambiguous wording such as:

- Fluent
- Professional proficiency
- Business-level
- Excellent language skills
- Strong communication skills in the language

Return `Flag` for ambiguous wording when it may imply a high practical
requirement. Return `Pass` for language described only as `preferred`, `a plus`,
`nice to have`, or equivalent.

The model must quote or capture the relevant job-description wording and must
not infer an unstated mandatory requirement.

### 3.5 Mandatory credentials

Return `Fail` only when:

- a licence, statutory qualification, certification, or security clearance is
  explicitly mandatory; and
- the candidate is known not to possess it.

Preferred credentials, tools, industry experience, and experience-year gaps
belong in fit assessment rather than hard-disqualifier screening.

### 3.6 Field-based work and travel

- A role whose primary working model is `Außendienst`, field sales, or sustained
  customer-site work -> `Fail`
- Explicit travel requirement <= 10% -> `Pass`
- Explicit travel requirement > 10% -> `Fail`
- `Occasional travel` without a percentage -> `Flag`, then proceed
- No travel statement -> `Pass`

Customer-facing work and occasional customer visits are not sufficient evidence
that a role is field-based.

## 4. Conditions That Do Not Filter This Track

The initial test applies no hard exclusion for:

- Remote, hybrid, or on-site working model
- Job location
- EU or UK remote roles
- Work authorization
- Part-time work
- Industry attractiveness
- Company or mission attractiveness
- Debatable seniority differences inside the candidate's band
- Experience-year gaps below the rule 3.1(b) threshold (minimum required < 5
  years), including the 3–5 year `Flag` band
- Customer segment, product complexity, or transferable domain experience

These items may be recorded or assessed later, but they do not belong in this
hard-disqualifier stage. Note the boundary with rule 3.1: an **explicit**
minimum requirement of 5+ years, or an **explicit** people-management mandate,
is a hard disqualifier under 3.1(b)/(c); only sub-threshold or debatable
seniority differences remain outside this stage.

## 5. Required Evidence

For every `Fail`, `Unknown`, or `Flag`, retain:

- the rule that was evaluated;
- the exact or minimally sufficient job-description evidence;
- the resulting state; and
- a short reason without unsupported inference.

## 6. Versioning

- Never overwrite the policy version attached to an existing evaluation.
- Every evaluation record must store `hard_disqualifier_policy_version`.
- A material change to a threshold, accepted contract type, language rule, or
  travel rule creates a new policy version.
- Typographical clarifications that do not alter decisions may update this file
  without changing the policy version, but should be recorded in version control.

### Version history

- `v0.1` — initial accepted policy (career stage, compensation, contract,
  language, credentials, field/travel).
- `v0.2` (accepted 2026-08-12) — rule 3.1 reframed as a two-sided
  career-stage / seniority-band mismatch: added (b) explicit 5+ year requirement
  (`Fail`; 3–5 years `Flag`) and (c) explicit people-management / team-leadership
  mandate (`Fail`). Reconciled Section 4 accordingly. Requires recall-impact
  logging for the new triggers.

### Freeze note

`v0.2` is frozen for the next prospective collection and evaluation run. No
threshold, trigger, or output-state change may be made after that run starts.
Every job excluded by rule 3.1(b) or 3.1(c) remains in the run audit and recall-
impact log. Any proposed change discovered during the run is recorded for a
later version and is not applied retroactively to the frozen batch.
