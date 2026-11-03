# Capability Fit Policy

Policy version: `capability-fit-v0.4`
Status: Draft (2026-10-29). Design agreed on 2026-10-28; thresholds are under
calibration against the 15-job test (Section 10) and must be frozen before the
next prospective run.
Decision stage: Capability-fit assessment
Supersedes: `capability-fit-v0.3` (archived in
[`archive/CAPABILITY_FIT_POLICY_v0.3.md`](archive/CAPABILITY_FIT_POLICY_v0.3.md))

Changes from v0.3 (consolidating the manual Job Fit Rubric v2 into this
policy):

- Reading the job now produces a **problem statement** and a **candidate
  profile from the hiring manager's side**, before any skill work.
- Only the **5 most critical hard skills** are output, ranked. Skill #1 is the
  one that solves the problem statement. The three-core-skill marking is
  removed.
- Evidence matching breaks every skill into **action, operating object, goal,
  and context** on both the JD and the CV side, and assigns one of four states:
  **Direct / Adjacent / Transferable / Missing**, plus **ownership**.
  CV silence is now `Missing` (v0.3: `unconfirmed`).
- The label is **Fit / Stretch / Not fit**, derived by code from a 0–10 skill
  score with a skill-#1 guard and a PM/PO cap (v0.3: Strong / Plausible /
  Weak / Unclear).
- Edge signals from rubric v2 are not part of this stage.

## 1. Purpose

This policy defines the capability-fit assessment for every job that passes
the hard-disqualifier stage. It answers:

> How credible is the candidate for this role, judged on real evidence for the
> skills the job depends on most?

The output is a **skill map** (the five most critical hard skills and the
candidate's evidence for each) and a **label** that sets review priority. The
label is not an application gate: every job that passes the hard
disqualifiers stays visible, including `Not fit`, and the human makes the
final decision.

## 2. Scope and Boundary

Run this assessment only after the job passes the shared hard-disqualifier
policy. Do not re-run or reconsider that stage. In particular, language,
years of experience, seniority, contract, location, and function are decided
there and are not scored again here.

Capability fit does not assess:

- personal interest, attractiveness, or company desirability;
- what the candidate could do after CV changes or portfolio work;
- general learnability without current evidence;
- competitive edge against the applicant pool; or
- the final Apply / Do not apply decision.

## 3. Structure

| Step | Question | Sees the CV? | Output |
|---|---|---|---|
| A. Read the job | What problem is the role hired to solve, who would the hiring manager picture, and which five hard skills matter most? | **No** | Problem statement, candidate profile, top 5 skills (ranked), industry |
| B. Match evidence | For each of the five skills, what is the candidate's evidence? | Yes | Four-part comparison, state, ownership, reasoning |
| C. Label | Score and label | Code | Score, label |
| D. Supporting detail | What sector is it, and how was the call reached? | n/a | Industry/sector, reasoning trail |

Separation rules:

- Step A describes the job only. A skill must never be omitted, reworded, or
  re-ranked because of what the candidate has or lacks.
- Step B must return exactly one evidence entry for each of the five skills
  and must not add, drop, rename, or re-rank them.
- The label is derived by code (Section 7). The model never chooses it.

## 4. Step A: Read the Job (CV-blind)

### 4.1 Problem statement

One sentence from the hiring manager's side:

> They need someone who …, because ….

If the problem cannot be written from the JD, the posting is too thin to
assess. Record `insufficient_jd` and the reason; the label is `Not fit` with
that reason shown, and the job stays visible for human review. A posting this
vague is often a "zombie" posting (for example, a recruiting agency collecting
candidates without a concrete vacancy), so it does not deserve tailoring time.

### 4.2 Candidate profile (hiring manager's view)

Two or three lines describing the person the hiring manager pictures in the
seat: background, typical prior role, the experience and tools they would
expect. This describes the job, not the candidate.

### 4.3 The five most critical hard skills

The model reads the full JD and identifies every hard skill internally, but
outputs only the **five most critical**, ranked most critical first.

What counts as a hard skill (unchanged from v0.3):

- a capability a CV can evidence and a reviewer can check;
- category `tool`, `method`, or `credential`.

Exclude:

- **languages**, which are decided by Hard Disqualifier rule 3.4;
- soft skills and personal traits (communication, teamwork, proactivity,
  hands-on mentality, and similar);
- years of experience and seniority wording (Hard Disqualifier 3.1);
- formal education and degree requirements (experience is weighted over
  degrees);
- employment conditions (location, contract, compensation, travel); and
- the industry itself, which is recorded separately (Step D).

Ranking rules:

- **Skill #1 is the skill that most directly solves the problem statement.**
  If #1 does not connect to the problem statement, the ranking is wrong.
- A skill is critical when its absence would make a hiring manager see a
  basic mismatch, not something to learn on the job. `Required` wording alone
  does not make a skill critical; a `preferred` skill ranks high only when the
  responsibilities show the role cannot function without it.
- A specific tool ranks high only when operating that tool is itself central
  to the role. When a comparable tool would plausibly do, name the underlying
  method or the tool category instead.
- Name each skill with the qualifiers the JD makes material ("B2B SaaS
  customer onboarding and adoption", not "Onboarding"), one verifiable
  capability per skill.
- If the JD yields fewer than five hard skills, output all of them. The label
  uses percentages, so fewer skills are judged fairly.

For each skill record:

- `rank`: 1–5;
- `skill`: the skill name with its material qualifiers;
- `category`: `tool` | `method` | `credential`;
- `jd_signal`: `required` | `preferred` | `responsibility`;
- `jd_quote`: the shortest sufficient JD wording; and
- the JD side of the four-part breakdown (Section 5.1).

## 5. Step B: Evidence Matching

### 5.1 Four-part breakdown

Every skill is broken down into the same four parts on **both** the JD side
and the CV side before a state is assigned:

| Part | Question |
|---|---|
| **Action** | What is done? (onboard, train, configure, analyse, coordinate…) |
| **Operating object** | On whom or what? (consumers, enterprise end users, pharma clients, patients, CRM data, hardware…) |
| **Goal** | To achieve what? (tool adoption, programme enrolment, renewal, on-time delivery…) |
| **Context** | Under what conditions? (B2B/B2C, segment, tool, scale, depth) |

The state follows from which parts differ. A shared verb or keyword alone
never makes evidence `Direct`. This is semantic matching, not keyword
matching.

### 5.2 States

| State | Rule | How the evidence may be used |
|---|---|---|
| **Direct** | Action, operating object, and goal all match. Context may differ slightly | Claim as is, within the recorded scope |
| **Adjacent** | Action, operating object, and goal match, but the **context** shifts materially: a different tool in the same category, a different customer segment, or a narrower depth | Claim with one qualifying phrase |
| **Transferable** | The action matches, but the **operating object or the goal** differs | Needs a reframing story; never present as direct experience |
| **Missing** | No relevant evidence in the CV | Gap |

`Adjacent` is stronger than `Transferable`: an adjacent skill is the same work
in a different setting; a transferable skill is the same kind of work on a
different thing or for a different purpose.

**CV silence is `Missing`.** If the candidate later adds evidence, the CV or
Candidate Profile is updated and later jobs are matched against it.

### 5.3 Ownership

Every non-`Missing` entry records ownership:

- `Owned`: the candidate owned the work (led, owned, was accountable for it);
- `Contributed`: the candidate took part in work someone else owned
  (supported, contributed to, was part of a team that…).

### 5.4 Worked example

JD skill: "Enterprise SaaS end-user onboarding and adoption".

| | JD | CV |
|---|---|---|
| Action | Onboard, educate | Onboard, explain |
| Operating object | **Enterprise employees** (tool users) | **Patients** in a programme |
| Goal | **Tool adoption in a workflow** | **Programme enrolment** |
| Context | B2B SaaS | B2B2C pharma service |

The operating object and the goal both shift → **Transferable**, not Direct.
What carries over: running a structured onboarding flow, stakeholder
communication, measuring activation.

### 5.5 Fields

For each of the five skills:

- `rank` (must match Step A);
- `cv_evidence`: the CV item, employer or project, and what was done, with the
  concrete result where the CV gives one; null for `Missing`;
- CV-side `action`, `operating_object`, `goal`, `context`; null for `Missing`;
- `state`: `Direct` | `Adjacent` | `Transferable` | `Missing`;
- `ownership`: `Owned` | `Contributed`; null for `Missing`; and
- `reasoning`: one or two sentences naming which parts match and which shift.
  It explains the one assigned state and must not suggest a stronger one.

Background that only shares the setting (same industry, same product type)
without the functional work is not evidence. Learnability, aptitude, and
inference beyond the CV are not evidence.

## 6. Scoring

Each skill scores:

| Score | Condition |
|---|---|
| **2** | `Direct` and `Owned` |
| **1** | `Direct` and `Contributed`, or `Adjacent`, or `Transferable` |
| **0** | `Missing` |

The total runs from 0 to 2 × the number of skills (0–10 for five skills).
The score share is total ÷ maximum. Adjacent and Transferable score the same;
the distinction stays in the reasoning because it tells the candidate how much
reframing a CV or interview needs.

The score is computed by code from the states. The model does not produce a
score.

## 7. Label Rules

Apply in order:

```text
Skill #1 is Missing                   -> Not fit   (regardless of total)
Score share >= 60%                    -> Fit
Score share >= 30%                    -> Stretch
Otherwise                             -> Not fit

Then: role family is PM / PO and label is Fit -> Stretch
```

With five skills: Fit = 6–10, Stretch = 3–5, Not fit = 0–2. The 60% line
corresponds to about three fully owned skills; partial evidence alone cannot
reach Fit.

The PM / PO cap comes from the role-family decision recorded by Hard
Disqualifier rule 3.8 ("PM/PO stretch family").

Examples (D = Direct and Owned, P = partial, M = Missing):

| Skills #1–#5 | Score | Label |
|---|---|---|
| D, D, D, M, M | 6 | Fit |
| D, P, P, P, P | 6 | Fit |
| D, D, P, M, M | 5 | Stretch |
| P, P, P, P, P | 5 | Stretch |
| D, P, M, M, M | 3 | Stretch |
| D, M, M, M, M | 2 | Not fit |
| M, D, D, D, D | 8 | Not fit (#1 Missing) |

## 8. Step D: Supporting Detail

Supporting detail explains the result and never changes the label.

- **Industry / sector**: the sector the role operates in, as evidenced by the
  JD (for example "B2B SaaS – compliance automation"), with `jd_signal`:
  `required` (industry experience required), `preferred` (a plus), or
  `context_only` (apparent but not asked for).
- **Reasoning trail**: one line per step, so the reviewer can see where the
  call turned. Example:

  > Problem: they need someone to build the operating engine of Customer
  > Success … · #1 CS operating-model design: Transferable (object: launch
  > workflow vs CS function) · #5 pilot → measure → scale or kill: Direct,
  > owned · Score 6/10 = 60% → **Fit** · Industry: B2B SaaS, carbon accounting
  > (context only).

Further supporting fields (title flag, company stage, pay against target,
domain advantage) are deferred to a later version.

## 9. Required Output

The model produces Steps A, B, and the industry part of D. It must not produce
a label, a score, an attractiveness assessment, or an Apply / Do not apply
recommendation. Code derives the score and label.

```yaml
capability_fit:
  policy_version: capability-fit-v0.4
  problem_statement: "They need someone who … because …"
  candidate_profile: "…"
  insufficient_jd: false
  skills:                       # Step A, CV-blind, ranked, max 5
    - rank: 1
      skill: B2B SaaS customer onboarding and adoption
      category: method
      jd_signal: required
      jd_quote: "Own onboarding of new customers …"
      jd: {action: …, operating_object: …, goal: …, context: …}
  evidence:                     # Step B, one entry per skill
    - rank: 1
      cv_evidence: "Smartpatient CSM: improved onboarding funnel (enrolment 76→83%)"
      cv: {action: …, operating_object: …, goal: …, context: …}
      state: Transferable
      ownership: Owned
      reasoning: "Object (patients vs SaaS users) and goal (enrolment vs adoption) shift."
  industry:
    industry: B2B SaaS – compliance automation
    jd_signal: context_only
    jd_quote: "…"
  # derived by code, not by the model:
  score: 6
  score_max: 10
  label: Fit
  reasoning_trail: "…"
```

## 10. Calibration and Open Items

The design was first tested on 15 Indeed postings on 2026-10-28
(`Fit_Test_15_jobs_2026-10-28.xlsx`, kept outside this repository). Seven
passed the hard disqualifiers (3 Fit, 2 Stretch, 2 Not fit); the eight
excluded jobs were also scored, only for calibration. The candidate's own
calls on these jobs become the labelled set for the decisions below. Any rule
change must re-pass that set.

Open items to settle before freezing v0.4:

1. **Stretch threshold.** At 30%, roles scored only on Transferable/Adjacent
   points (furniture sales advisor, wholesale sales coordinator) reach
   Stretch. Option: Stretch requires at least one `Direct` + `Owned` skill, or
   raise the line to 40%.
2. **Fit with a single Direct skill.** D, P, P, P, P reaches 60%, including
   when #1 is only Transferable. Option: Fit also requires #1 to be `Direct`,
   or at least two `Direct` + `Owned` skills.
3. **Skill-#1 guard on tools.** A missing tool at #1 (for example HubSpot
   administration) forces Not fit even when the process half of the role is a
   strong match. Decide whether the guard applies when #1 is a `tool`.
4. **Tool names in the CV.** Many `Missing` states come from tools not named in
   the CV (HubSpot, ticketing systems, Notion/ClickUp). These are candidate-side
   updates, not policy changes.

Human review: record each disagreement with the step where it arises:
problem statement, skill selection or ranking (A), breakdown or state (B), or
the label rule (C). The step shows which part of the policy needs work.

The hypothesis to test, not to assume:

```text
Fit interview rate > Stretch interview rate > Not fit interview rate
```

## 11. Versioning

- Every assessment record must store `fit_policy_version`.
- Existing assessments keep the policy version under which they were made.
  v0.2 and v0.3 records are not re-labelled.
- Changes to the steps, evidence states, scoring, thresholds, label rules, or
  required outputs require a new policy version.
- Editorial clarifications that do not alter decisions may remain within the
  current version and should be recorded in the changelog.

### Version history

- `v0.2`: holistic fit judgment on the few most important responsibilities
  (archived outside this repository).
- `v0.3` (2026-09-10): full hard-skill decomposition, three core skills, five
  evidence states, Strong / Plausible / Weak / Unclear label.
- `v0.4` (draft, 2026-10-29): problem statement and hiring-manager profile;
  top five ranked skills; four-part semantic breakdown; Direct / Adjacent /
  Transferable / Missing with ownership; 0–10 score; Fit / Stretch / Not fit
  with the skill-#1 guard and PM/PO cap.
