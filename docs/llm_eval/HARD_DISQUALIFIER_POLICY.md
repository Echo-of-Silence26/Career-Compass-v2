# Hard-Disqualifier Policy

Policy version: `hard-disqualifier-v0.4`
Status: Accepted 2026-11-03. Must be frozen before the next prospective run.
Decision stage: Hard-disqualifier screening
Supersedes: `hard-disqualifier-v0.3` (archived in
[`archive/HARD_DISQUALIFIER_POLICY_v0.3.md`](archive/HARD_DISQUALIFIER_POLICY_v0.3.md))

Changes from v0.3 (decision of 2026-11-03):

- 3.1(b): the functional experience threshold is loosened. A minimum
  requirement of **up to 3 years** now passes; **more than 3 years** is a
  `Fail` (v0.3: 3 years or more was a `Fail`). The general-experience `Flag`
  moves to the same line.

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

Only what the posting **states** can produce a `Fail`. A suspected but unstated
trigger is `Unknown` or `Flag`, never `Fail`.

## 3. Hard Disqualifiers

### 3.1 Career stage / seniority band mismatch

The candidate targets a junior-to-mid individual-contributor band (up to three
years required in the function). A role is excluded when its career stage falls
clearly **outside that band on either side**: too junior (entry programmes) or
too senior (a functional floor above three years, a senior title, or a
people-management mandate).

**(a) Below band: entry programmes.** Return `Fail` when the role is explicitly:

- Internship / Praktikum
- Working Student / Werkstudent
- Graduate Programme

Trainee and Associate roles (for example "Trainee Customer Success",
"Associate Product Manager") are in band -> `Pass`.

Part-time work is not excluded on this basis.

**(b) Above band: explicit functional experience-year requirement.** Anchored
on the **minimum required years** stated for the role's core function, not on
preferred or "nice to have" years:

- Minimum required years **in the role's function** (for example, "4+ years in
  Customer Success", "at least 5 years of product management experience")
  **> 3** -> `Fail`
- Minimum required years **<= 3** (for example, "3+ years in Customer
  Success") -> `Pass`
- **> 3** years of general professional experience with no function named
  (for example, "5+ years of work experience") -> `Flag`, then proceed
- No explicit number stated, or the years apply only to a preferred/"plus"
  qualification -> `Unknown` (do not infer a floor)

Ambiguous seniority wording with no number, such as `several years`,
`proven track record`, or `extensive experience`, returns `Flag`, not `Fail`.
When a range is given (for example, `3-5 years`), use the lower bound as the
minimum required.

**(c) Above band: explicit people-management / team-leadership mandate.** Return
`Fail` when the job description explicitly assigns responsibility for a team in
**any** of the following forms, and the candidate has no people-management
evidence (direct or transferable):

- **Managing / leading a team**: owning direct reports or headcount (not merely
  coordinating a project);
- **Building / setting up a team**: hiring, recruiting, or standing up a new
  team or function;
- **Developing a team**: coaching, growing, or performance-managing reports.

Do not trigger on individual-contributor leadership wording such as `mentor`,
`lead initiatives`, `lead projects`, `thought leadership`, or `lead by example`.
Ambiguous wording that could mean either people management or IC influence
returns `Flag`, then proceeds.

**(d) Above band: senior title.** Return `Fail` when the job title explicitly
carries a senior level: `Senior` / `Sr.`, `Staff`, `Principal`, `Head of`,
`Director`, `VP` / `Vice President`, or `Leiter/in` / `Leitung`. A bare `Lead`
in the title without a people-management mandate (for example, "Lead Product
Manager") returns `Flag`. A level wording only in the body text, not the title,
is handled by (b) or (c).

The model must quote the job-description wording for any `Fail` or `Flag` under
(b), (c) or (d) and must not infer an unstated year floor, management mandate,
or level.

### 3.2 Compensation (retired in v0.3)

No compensation threshold applies, because the candidate considers both
full-time and part-time roles. Do not evaluate or return an entry for 3.2.
The number is kept unused so that rules 3.3–3.8 keep stable IDs.

### 3.3 Contract type

The test is duration: only an **open-ended (unbefristet)** engagement passes.
The employment model does not matter.

Return `Fail` when the engagement is explicitly time-limited:

- Fixed-term / befristet / zeitlich befristet (including fixed-term with an
  option to convert, such as "Option auf Übernahme")
- Temporary or project-limited contract with a stated end date or duration
  (for example "6-month contract")
- Maternity or parental-leave replacement (Elternzeitvertretung,
  Mutterschutzvertretung)

Return `Pass` when the posting states permanent / unbefristet / open-ended
engagement. Agency employment (Arbeitnehmerüberlassung, Zeitarbeit) and
contractor or freelance engagements (freie Mitarbeit) do **not** trigger this
rule by themselves. They fail only when they are also explicitly time-limited.
Return `Unknown` when the duration is not stated.

### 3.4 Real-time spoken German gate

Return `Fail` only when the posting shows that **real-time spoken German with
German speakers is a core daily task** of the role, for example:

- phone calls or live meetings with German-speaking customers, patients, or
  partners as a main part of the job;
- German-language sales calls;
- German-language frontline or phone support.

Do not trigger on:

- reading or writing German (documents, email, tickets, written support);
- a German-speaking employer whose live client conversations are with
  international clients in English;
- German described as `preferred`, `a plus`, `nice to have`, or equivalent.

Return `Flag` when German is required at a high level (`fluent`, `fließend`,
`verhandlungssicher`, C1/C2, native) but the posting does not show whether it
is spoken in real time with German speakers as a core task. Also return `Flag`
when the role clearly runs on German business workflows all day (German
meetings, documents, and colleagues) without a client-facing speaking task.
Return `Pass` when no German requirement is stated or German is only a plus.

The model must quote the job-description wording for any `Fail` or `Flag` and
must not infer a speaking requirement from the company's location or language
alone.

### 3.5 Mandatory credentials

Return `Fail` only when:

- a licence, statutory qualification, certification, Ausbildung, or security
  clearance is explicitly mandatory (for example ZMF/ZMV, MFA); and
- the candidate is known not to possess it.

Preferred credentials, tools, industry experience, and experience-year gaps
below the 3.1(b) threshold belong in fit assessment rather than
hard-disqualifier screening.

### 3.6 Field-based work and travel

- A role whose primary working model is `Außendienst`, field sales, or sustained
  customer-site work -> `Fail`
- Explicit travel requirement <= 10% -> `Pass`
- Explicit travel requirement > 10% -> `Fail`
- `Occasional travel` without a percentage -> `Flag`, then proceed
- No travel statement -> `Pass`

Customer-facing work and occasional customer visits are not sufficient evidence
that a role is field-based.

### 3.7 Location

The role must be workable from **München**, **Berlin**, or **fully remote from
Germany**.

- On-site or hybrid in München or Berlin (including their commutable
  metropolitan area, for example Garching or Potsdam) -> `Pass`
- Fully remote and workable from Germany (worldwide, EU/EMEA, or
  Germany-wide remote) -> `Pass`
- A posting that lists several locations including München or Berlin -> `Pass`
- On-site or hybrid **only** in another city -> `Fail`
- Remote restricted to a region or residency that excludes Germany (for
  example "US only", "must be based in the UK") -> `Fail`
- Remote with recurring on-site presence in another city (for example "one
  week per month in Hamburg") -> `Flag`
- The JD and the job record's location fields disagree -> `Flag`
- No location or work mode stated -> `Unknown`

Use the JD text first and the job record's `city`, `country`, and `work_mode`
fields as supporting evidence.

### 3.8 Function / role family

Judge the role's **primary function** from its responsibilities, not from the
title alone.

In scope -> `Pass`:

- **Customer Success**: CSM, account management without a sales quota,
  partner or client success, customer support;
- **Implementation and onboarding**;
- **Operations**: business, GTM, revenue, or marketing operations; program and
  project management, including marketing project management;
- **B2B or B2C go-to-market** roles that are not pure sales or growth
  marketing (for example GTM manager, launch, partnerships);
- **Product Manager / Product Owner**. In scope but a stretch family: `Pass`,
  and the `reason` must say "PM/PO stretch family" so the fit stage can see it.

Out of scope -> `Fail` when the primary function is clearly:

- **Growth or acquisition marketing**: performance, paid acquisition, growth
  marketing, SEO/SEA, brand, content, or social media marketing;
- **Pure quota-carrying sales**: SDR, BDR, Account Executive;
- **Finance, accounting, or audit**;
- **A pure specialist function**: for example software or data engineering,
  data science, design, legal, clinical, regulatory, or quality roles.

Return `Flag` when the role mixes an in-scope and an out-of-scope function and
neither clearly dominates (for example a CSM role with a stated upsell quota,
or product marketing). Return `Unknown` only when the posting is too thin to
identify the primary function.

### 3.9 Recall-impact logging

Rules 3.1(b), 3.1(d), 3.3, 3.7 and 3.8 were introduced or tightened in
v0.3 and are non-compensatory. Every job they exclude must be logged with its
`job_id`, the triggering rule, and the quoted job-description evidence, so the
recall cost (potentially workable roles that were removed) can be reviewed
later. Rule 3.1(c) keeps its logging requirement from v0.2.

## 4. Conditions That Do Not Filter This Track

This policy applies no hard exclusion for:

- Part-time work
- Compensation (3.2 retired; the stated salary may be recorded for review)
- Work authorization, except where a remote role's residency restriction
  excludes Germany (3.7)
- Industry attractiveness
- Company or mission attractiveness
- Debatable seniority differences inside the candidate's band, including
  `Flag` cases under 3.1(b) and 3.1(d)
- Experience-year gaps within the 3.1(b) threshold (minimum required <= 3
  years in the function)
- Customer segment, product complexity, or transferable domain experience
- Posting age. Sourcing limits collection to recent postings (see the sourcing
  config); this stage does not re-check it.

These items may be recorded or assessed later, but they do not belong in this
hard-disqualifier stage.

## 5. Required Evidence

For every `Fail`, `Unknown`, or `Flag`, retain:

- the rule that was evaluated;
- the exact or minimally sufficient job-description evidence;
- the resulting state; and
- a short reason without unsupported inference.

## 6. Versioning

- Never overwrite the policy version attached to an existing evaluation.
- Every evaluation record must store `hard_disqualifier_policy_version`.
- A material change to a threshold, accepted contract type, language rule,
  travel rule, location rule, or function scope creates a new policy version.
- Typographical clarifications that do not alter decisions may update this file
  without changing the policy version, but should be recorded in the changelog.

### Version history

- `v0.1`: initial accepted policy (career stage, compensation, contract,
  language, credentials, field/travel).
- `v0.2` (accepted 2026-08-12): rule 3.1 reframed as a two-sided
  career-stage / seniority-band mismatch: added (b) explicit 5+ year requirement
  (`Fail`; 3–5 years `Flag`) and (c) explicit people-management / team-leadership
  mandate (`Fail`). Reconciled Section 4 accordingly. Requires recall-impact
  logging for the new triggers.
- `v0.3` (accepted 2026-10-28): consolidated the manual Job Fit Rubric v2
  knockouts. 3.1(a) Trainee removed from the entry-programme list (Trainee and
  Associate pass); 3.1(b) tightened to 3+ functional years; 3.1(d) senior title added;
  3.2 compensation threshold retired; 3.3 unbefristet only, agency and
  contractor allowed; 3.4 replaced
  by the real-time spoken German gate; 3.7 location and 3.8 function / role
  family added; recall-impact logging extended (3.9).
- `v0.4` (accepted 2026-11-03): 3.1(b) loosened from `>= 3` to `> 3` years;
  a minimum of exactly 3 years in the function now passes. The
  general-experience `Flag` follows the same line.

### Freeze note

Freeze `v0.4` before the next prospective collection and evaluation run. After
that run starts, no threshold, trigger, or output-state change may be made.
Every job excluded under the rules listed in 3.9 remains in the run audit and
recall-impact log. Any proposed change discovered during the run is recorded
for a later version and is not applied retroactively to the frozen batch.
