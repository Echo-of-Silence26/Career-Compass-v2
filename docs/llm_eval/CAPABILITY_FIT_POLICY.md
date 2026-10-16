# Capability Fit Policy

Policy version: `capability-fit-v0.3`
Status: Draft. The structure was accepted on 2026-09-10 and revised the same
day, per the user's decisions on industry, education, top-3 core skills, and
the five evidence states. On 2026-09-11 every evidence entry gained a required
`reasoning` field and the skill-map table view was added (Section 9.1). The
policy must be frozen before the next prospective run.
Decision stage: Capability-fit pre-assessment
Supersedes: `capability-fit-v0.2` (archived outside this repository)

Changes from v0.2:

- The unit of assessment changes from "the few most important
  responsibilities" to a full **hard-skill list** decomposed from the JD.
- The single combined judgment is split into three separately stored layers:
  **(1) hard-skill decomposition → (2) marking the three most central skills →
  (3) per-skill evidence matching**. Evidence matching covers every skill, not
  only the three core ones.
- Evidence uses **five states**: `done` / `participated` / `adjacent` /
  `unconfirmed` / `not_done`. Each state tells downstream use (review, resume
  material) how the evidence may be used. Absence from the CV is
  `unconfirmed`, not a gap.
- **Industry is a separate variable, parallel to the hard skills.** It is
  extracted and matched on its own and is never folded into a skill or counted
  as a shifted dimension.
- The label is derived from the three core skills by a fixed rule (Section 8).
  The model no longer picks it holistically.
- `core_matches` and `key_gap` are replaced by the full per-skill table.
- Every evidence entry carries a `reasoning` that explains its state. The
  skill map is reviewed as a three-column table (Requirement / Your evidence /
  Assessment), in which code prints a fixed verdict for each state
  (Section 9.1).

## 1. Purpose

This policy defines the capability-fit assessment for all target role families.

The main output is a **skill map** for each job: the hard skills the job needs,
the three most central of them, and the candidate's evidence state for each
one. The skill map tells the candidate what to prepare, which experience can
be used as-is, which must be framed carefully, and what still needs
confirming. It can also be aggregated across jobs (for example, "80% of Growth
roles ask for SQL and the CV has no evidence of it").

The Fit label is secondary. It exists to:

1. reduce the time needed for human job review; and
2. test whether the labels distinguish job groups with different interview
   outcomes.

The assessment must remain simple. A criterion should not be added unless it
improves the skill map, helps distinguish clear fit from clear mismatch,
explains materially different market outcomes, or reduces human review effort.

## 2. Scope and Boundary

Run this assessment only after the job passes the shared hard-disqualifier
policy. Do not re-run or reconsider that stage.

Capability fit asks:

> Which hard skills does this role need, which three matter most, what
> industry is it in, and what is the candidate's evidence state for each?

Capability fit does not assess:

- personal interest or attractiveness;
- company or industry desirability;
- what the candidate could do after major CV changes or portfolio work;
- general learnability without current evidence; or
- the final Apply / Do not apply decision.

All results remain subject to human review. The system stops after producing
this assessment and does not turn it into an application recommendation.

## 3. Structure

The layers are produced in order. Each is stored as a separate field, and a
later layer must not rewrite an earlier one.

| Layer | Question | Sees the CV? | Sees the core marking? |
|---|---|---|---|
| 1. Hard-skill decomposition | Which hard skills does this JD require? | **No** | n/a |
| 2. Core marking | Which three skills are most central? | **No** | n/a |
| Industry (parallel) | Which industry is this role in, and does the JD require industry experience? | **No** | n/a |
| 3. Evidence matching | What is the candidate's evidence state for each skill, and for the industry? | Yes | **No** |
| Label | Aggregate the core skills' states | (code) | (code) |

Separation rules:

- Layers 1–2 and the industry field describe the job, so they are produced
  **without the Candidate Profile**. A skill must never be omitted, reworded,
  or down-weighted because of what the candidate has or lacks.
- Layer 2 must not add, remove, merge, or rename Layer 1 skills. It only marks
  three of them.
- Layer 3 receives the full Layer 1 skill list and the industry **without the
  core marking**. It must return exactly one evidence entry for every skill,
  plus one for the industry. Evidence matching is not pruned by importance.
- The core marking affects only the label (Section 8). It never decides which
  skills get matched or appear in the output.

## 4. Layer 1: Hard-Skill Decomposition

### 4.1 What counts as a hard skill

A hard skill is a capability that a CV can evidence and a reviewer can check.
Each skill has one `category`:

- `tool`: a named software product, platform, or programming/query language
  (for example, Salesforce, HubSpot, Google Ads, SQL, SAP BW, Jira).
- `method`: a practice, technique, functional capability, or specialised
  knowledge area (for example, A/B testing, B2B lead generation, SEO, customer
  onboarding programme design, category management, backlog prioritisation,
  GDPR compliance).
- `language`: a spoken or written language at a stated or implied level.
- `credential`: a certification or licence (for example, PSPO, PMP).

Exclude from the skill list:

- **industry**, which is a separate parallel variable (Section 6);
- soft skills and personal traits (communication, teamwork, proactivity,
  structured thinking, hands-on mentality, and similar). Every CV claims them
  and no CV evidence can check them;
- years of experience and seniority wording, which belong to Hard
  Disqualifier rule 3.1;
- formal education and degree requirements. The candidate has several years of
  work experience, and experience is weighted over degrees (decision of
  2026-09-10); and
- employment conditions (location, contract type, compensation, travel), which
  belong to Hard Disqualifier.

### 4.2 Granularity and wording

- List every distinct hard skill the JD **requires, prefers, or clearly depends
  on through a listed responsibility**. Do not drop a skill for being minor.
  Importance belongs to Layer 2.
- Name each skill **with the functional qualifiers the JD makes material**, so
  Layer 3 can judge it without guessing. Write "Enterprise SaaS end-user
  onboarding and adoption", not "Onboarding". Write "B2B lead generation via
  paid channels", not "Lead generation". Do not put the industry into skill
  names. Industry is captured once, in Section 6.
- One skill per verifiable capability. Do not merge two distinct skills into
  one entry ("SEO and paid social"), and do not split one skill into synonyms.
- A skill named only as an example inside a list ("e.g. HubSpot, Salesforce or
  similar") is one skill ("CRM platform"), not one per example.

### 4.3 Fields

For each skill:

- `skill_id`: a stable id within this assessment (`S1`, `S2`, ...);
- `skill`: the skill name with its material functional qualifiers;
- `category`: `tool` | `method` | `language` | `credential`;
- `jd_signal`: how the JD itself presents the skill. This is a factual reading,
  not a judgment:
  - `required`: stated as a requirement or must-have;
  - `preferred`: stated as a plus, nice-to-have, "ideally", or equivalent;
  - `responsibility`: not in the requirements list, but a listed
    responsibility clearly depends on it;
- `jd_quote`: the shortest sufficient JD wording that supports the skill.

## 5. Layer 2: The Three Core Skills

Mark the **three** skills the role's central function depends on most. If the
JD yields fewer than three hard skills, mark all of them. List them most
central first, each with a short `reason`.

Guidance:

- A core skill is one whose absence a hiring manager would treat as a basic
  mismatch, not something to learn on the job. Typical signals: it underpins a
  primary responsibility, or the JD presents it as a must-have for the central
  function.
- `jd_signal: required` does not automatically mean core, because JDs often
  list generic requirements. A `preferred` skill is core only when the
  responsibilities clearly show the role cannot function without it.
- A specific `tool` is core only when operating that tool is itself the
  central function (for example, "Salesforce Administrator"). When a
  comparable tool would plausibly do, prefer the underlying method.
- The `reason` must be short and specific, so a human reviewer can disagree
  with the choice.

## 6. Industry (Parallel Variable)

Industry is recorded once per job, next to the skill list rather than inside
it.

Decomposition (CV-blind):

- `industry`: the industry or sector the role operates in, as evidenced by the
  JD (for example, "FMCG e-commerce marketplace", "IT hardware distribution").
  Use null only when the JD does not reveal it;
- `jd_signal`: `required` (industry experience is stated as required),
  `preferred` (stated as a plus), or `context_only` (the industry is apparent
  but no industry experience is asked for);
- `jd_quote`: the shortest sufficient JD wording, or null when `industry` is
  null.

Matching: the industry gets one evidence entry using the same five states and
field rules as a skill (Section 7). It is recorded and shown in parallel with
the label but **does not change the label**.

## 7. Layer 3: Evidence Matching (Five States)

For **every** Layer 1 skill, and for the industry, assign exactly one evidence
state using only the Candidate Profile. Do not skip any skill, and do not treat
any skill as more or less important than another.

### 7.1 The five states

| State | Meaning | How the result may be used |
|---|---|---|
| `done` | The candidate has done it, with concrete evidence in the profile | Can be used for matching and resume material, but the recorded responsibility scope must be kept. Never inflate it. |
| `participated` | The candidate took part but did not independently own it | A partial match. Must not be turned into "fully responsible for" or "led". |
| `adjacent` | The candidate has related experience on a shifted object, customer, goal, context, delivery model, tool, or depth | State what transfers. Must not be presented as direct experience. |
| `unconfirmed` | The profile does not give enough information either way | Mark as pending confirmation. Must not be judged as "cannot do". |
| `not_done` | The profile **explicitly** states the candidate has not done it | Record as a gap. Do not ask about it again and do not invent evidence. |

Decision rules:

- **Silence is `unconfirmed`, not `not_done`.** A skill the CV does not mention
  is `unconfirmed`. Use `not_done` only when the Candidate Profile explicitly
  records that the candidate has not done it (for example,
  `people_management_evidence: none`, or an entry the candidate has confirmed
  as not done). Cite that statement.
- **`done` vs `participated`** turns on ownership. If the evidence shows the
  candidate owned the work, it is `done`. If it shows contribution to work
  someone else owned (supported, contributed to, was part of a team that...),
  it is `participated`.
- **`done`/`participated` vs `adjacent`** turns on whether it is the same skill
  as stated. A shared verb or keyword alone never makes evidence `done`. When
  the object, customer, goal, product context, delivery model, or tool
  differs from the skill as stated, the evidence is `adjacent`.
- Judge each skill against its wording and `jd_quote` from Layer 1. A context
  difference that the skill's wording does not name, including industry, is
  not a shifted dimension.
- A skill is often compound (a method plus a named channel, tool, or
  analysis). When the evidence establishes only part of it: if the missing
  part is **material** to the skill as worded, the state is `adjacent` with
  `depth`. If it is minor, the state stays `done` or `participated` and the
  `reasoning` names the part that is not established.
- Background that only shares the setting (same industry, same product type)
  without the functional work is not evidence. The state is `unconfirmed`, and
  the background may be mentioned in `reasoning`.
- Learnability, general aptitude, and inference beyond the profile are not
  evidence.

### 7.2 Shifted dimensions (for `adjacent`)

Every `adjacent` entry lists which dimensions shift, using these values:

- `object`: what or whom the action operates on, including the beneficiary;
- `customer`: the paying counterpart or customer segment (for example, B2B vs
  B2C, enterprise vs SMB);
- `goal`: what the action is meant to achieve;
- `product_context`: the product type or delivery surface named in the skill;
- `delivery_model`: how the work is delivered (for example, in-house vs
  external advisory, named-account vs pooled);
- `tool`: a comparable but different tool or platform;
- `depth`: the evidence covers a materially narrower slice of the skill than
  the JD requires.

Worked example (candidate's actual case):

- JD skill: "Enterprise SaaS end-user onboarding and adoption". The JD means
  teaching enterprise employees to operate the software and embedding it in
  their workflow.
- CV: "onboarding" means explaining to pharma clients how the service serves
  their patients.
- Same verb, but `object` (patients vs employees) and `goal` (explaining a
  service vs adopting software in a workflow) both shift. The result is
  `adjacent`, not `done`. The note states what transfers: running structured
  onboarding for a B2B client relationship.

### 7.3 Fields

For each skill (`skill_id` must match Layer 1) and for the industry:

- `state`: `done` | `participated` | `adjacent` | `unconfirmed` | `not_done`;
- `candidate_evidence`: the relevant CV evidence, written so a reader can
  check it without opening the profile. Give the evidence item id or profile
  section, the employer or project, and what was done, with its concrete
  result where the profile gives one (for example,
  `ev-06 cruise e-commerce (China): built performance-ads acquisition from
  scratch; CPA -50%`).
  Several items may be cited. Required for `done`, `participated`,
  `adjacent`, and `not_done`. For `not_done` it cites the explicit statement.
  Null for `unconfirmed`;
- `scope`: required for `done` and `participated`. It records the candidate's
  actual responsibility scope (for example, "owned two named pharma accounts
  end-to-end" or "contributed product-concept input; upsell owned by sales").
  Null otherwise;
- `shifted_dimensions`: non-empty for `adjacent`, empty otherwise;
- `reasoning`: required for **every** state. One or two sentences explaining
  the state to the candidate:
  - `done` / `participated`: what the evidence establishes, and any minor part
    of the skill as worded that it does not establish (Section 7.1). If it
    covers the whole skill, say so;
  - `adjacent`: what transfers and what does not, naming the shift;
  - `unconfirmed`: what the CV does not show, phrased so the candidate can
    confirm or deny it. Background that shares only the setting may be
    mentioned here;
  - `not_done`: the recorded gap.

  The reasoning explains the one assigned state. It must not suggest a second
  state (such as "direct evidence; partial match") or a stronger verdict than
  the state supports.

Also return `unknowns`: only missing **JD** information that could materially
change a state or the core marking. Candidate-side gaps belong in
`unconfirmed` entries, not here. Use an empty list when there are none.

## 8. Label Aggregation

The label is derived deterministically from the evidence states of the core
skills. The model does not choose it. Non-core skills and the industry never
change the label, but they remain in the skill map.

Apply the rules in order:

```text
No hard skill identified (JD too thin to decompose)
-> Unclear

Any core skill is `not_done`
-> Weak Fit

Any core skill is `unconfirmed`
-> Unclear          (confirmation could still change the label)

Every core skill is `done`
-> Strong Fit

No core skill is `done` (all are `participated` or `adjacent`)
-> Weak Fit

Otherwise (at least one core `done`, the rest `participated` or `adjacent`)
-> Plausible Fit
```

`Unclear` here means "resolve the pending confirmations first". The
`unconfirmed` entries say exactly what to confirm. These are categories, not
score bands. Do not create or infer a numerical fit score.

## 9. Required Output

The model must not produce a job summary, an attractiveness assessment, an
Apply / Do not apply recommendation, or a numerical score. The persisted
assessment has this shape:

```yaml
capability_fit:
  policy_version: capability-fit-v0.3
  label: PlausibleFit            # derived per Section 8, not model-chosen

  skills:                        # Layer 1, CV-blind
    - skill_id: S1
      skill: B2B lead generation via paid channels
      category: method
      jd_signal: required
      jd_quote: "Manage and scale B2B lead generation across paid and non-paid channels"
    - skill_id: S2
      skill: Structured growth experimentation
      category: method
      jd_signal: responsibility
      jd_quote: "Test new channels and scale what works"
    - skill_id: S3
      skill: Marketing automation / CRM platform
      category: tool
      jd_signal: required
      jd_quote: "Hands-on with HubSpot or a similar CRM"
    - skill_id: S4
      skill: SEO and website content management
      category: method
      jd_signal: preferred
      jd_quote: "SEO know-how is a plus"

  core_skills:                   # Layer 2, CV-blind, exactly 3, most central first
    - skill_id: S1
      reason: Lead generation is the role's primary responsibility.
    - skill_id: S2
      reason: Channel testing is how the lead-gen target is met.
    - skill_id: S3
      reason: Campaign execution runs through the CRM.

  industry:                      # parallel variable, CV-blind
    industry: Industrial procurement software (B2B SaaS)
    jd_signal: context_only
    jd_quote: "our AI procurement platform for industrial buyers"

  evidence:                      # Layer 3, core-blind, full table
    - skill_id: S1
      state: adjacent
      candidate_evidence: "ev-06 cruise e-commerce (China): built performance-ads acquisition from scratch; CPA -50%"
      scope: null
      shifted_dimensions: [customer]
      reasoning: Paid-channel acquisition transfers directly; it targeted B2C consumers, not B2B buyers.
    - skill_id: S2
      state: done
      candidate_evidence: "ev-03 health-app company: designed and ran hypothesis-driven acquisition-channel experiments"
      scope: Designed and ran the experiments; results informed leadership go/no-go.
      shifted_dimensions: []
      reasoning: Owned the test-and-decide loop for new channels. Scaling a winning channel afterwards is not described.
    - skill_id: S3
      state: unconfirmed
      candidate_evidence: null
      scope: null
      shifted_dimensions: []
      reasoning: The CV does not show hands-on HubSpot or other marketing-automation CRM use. Have you used one?
    - skill_id: S4
      state: unconfirmed
      candidate_evidence: null
      scope: null
      shifted_dimensions: []
      reasoning: No SEO or website content work appears in the CV. Have you done any hands-on?

  industry_evidence:
    state: adjacent
    candidate_evidence: "ev-01 health-app company: pharma accounts on a B2B SaaS health app"
    scope: null
    shifted_dimensions: [product_context]
    reasoning: B2B SaaS experience transfers; healthcare, not industrial procurement.

  unknowns:
    - The JD does not state whether campaigns are run in-house or via an agency.
```

In this example core S3 is `unconfirmed`, so the actual derived label would be
`Unclear` until the CRM question is answered. If S3 were confirmed `done` or
`adjacent`, the label would be `Plausible Fit`, since S2 is `done`.

### 9.1 Skill-Map Table (Review View)

The persisted assessment above is the system of record. For review, code
renders it as a skill-map table with one row per skill: core skills first
(most central first), then the other skills in Layer 1 order, then the
industry as the last row. The model does not write the table.

| Column | Content |
|---|---|
| Requirement | `skill`, marked ★ when core, with its `jd_signal` |
| Your evidence | `candidate_evidence`, plus `Scope:` for `done` / `participated`. "None found in CV" for `unconfirmed` |
| Assessment | The fixed verdict for the state, followed by `reasoning` |

The verdict is fixed per state, so rows stay comparable across jobs:

| State | Verdict |
|---|---|
| `done` | Direct evidence |
| `participated` | Partial match (contributed, not owned) |
| `adjacent` | Transferable (shifted: *dimensions*) |
| `unconfirmed` | Not shown in CV (to confirm) |
| `not_done` | Confirmed gap |

The example above renders as:

| Requirement | Your evidence | Assessment |
|---|---|---|
| ★ B2B lead generation via paid channels (required) | ev-06 cruise e-commerce (China): built performance-ads acquisition from scratch; CPA -50% | **Transferable (shifted: customer).** Paid-channel acquisition transfers directly; it targeted B2C consumers, not B2B buyers. |
| ★ Structured growth experimentation (responsibility) | ev-03 health-app company: designed and ran hypothesis-driven acquisition-channel experiments. Scope: designed and ran the experiments; results informed leadership go/no-go. | **Direct evidence.** Owned the test-and-decide loop for new channels. Scaling a winning channel afterwards is not described. |
| ★ Marketing automation / CRM platform (required) | None found in CV | **Not shown in CV (to confirm).** The CV does not show hands-on HubSpot or other marketing-automation CRM use. Have you used one? |
| SEO and website content management (preferred) | None found in CV | **Not shown in CV (to confirm).** No SEO or website content work appears in the CV. Have you done any hands-on? |
| Industry: Industrial procurement software (B2B SaaS) (context_only) | ev-01 health-app company: pharma accounts on a B2B SaaS health app | **Transferable (shifted: product_context).** B2B SaaS experience transfers; healthcare, not industrial procurement. |

## 10. Human Review and Validation

Every Strong, Plausible, Weak, and Unclear result is reviewed by the human
evaluator during the evaluation phase. The reviewer may disagree at any layer:
a missing or spurious skill (Layer 1), a wrong core choice (Layer 2), a wrong
industry reading, or a wrong evidence state (Layer 3). Record the layer of
each override, because it shows where the policy needs work.

When the candidate answers an `unconfirmed` question, record the answer in the
Candidate Profile, either as new evidence or as an explicit "not done"
statement. Later jobs asking for the same skill then resolve to `done` /
`participated` / `adjacent` / `not_done` and are not asked again.

The policy is useful only if it supports at least one intended result:

- a skill map the candidate actually uses to decide what to prepare;
- shorter human review time; or
- meaningful separation in interview outcomes among the fit-label groups.

An expected but unproven market pattern is:

```text
Strong Fit interview rate > Plausible Fit interview rate > Weak Fit interview rate
```

This is a hypothesis to test, not an assumption to encode as ground truth.

Capability Fit is an auxiliary label for prioritisation, explanation, and later
analysis. It is not an ingestion, visibility, or application gate. Every job
with no hard-disqualifier `Fail` is stored, remains visible, and is presented
for human review regardless of its Fit label. Historical application behaviour
is retained only as historical evidence and is not Capability Fit ground truth.

## 11. Versioning and Open Items

- Every assessment record must store `fit_policy_version`.
- Existing assessments keep the policy version under which they were made.
  v0.2 records are not re-labelled.
- Changes to layer definitions, evidence states, the aggregation rule, or
  required outputs require a new policy version.
- Editorial clarifications that do not alter decisions may remain within the
  current version and should be recorded in version control.

Settled on 2026-09-10: industry is a parallel variable, education is
excluded, exactly three core skills are marked, and evidence uses the five
states.

Open items to settle before freezing v0.3:

1. **Industry and the label.** The industry is matched and shown, but it does
   not affect the label. Revisit if `jd_signal: required` industry mismatches
   turn out to predict outcomes.
2. **"No core `done` → Weak Fit".** A job whose three core skills are all
   `participated` or `adjacent` is Weak Fit. Confirm this is not too harsh on
   real JDs.
3. **Volume of `Unclear`.** Because silence is `unconfirmed`, early runs may
   produce many `Unclear` labels until the Candidate Profile accumulates
   confirmed answers.
4. **Cross-job skill map.** Skill names are free text per JD. Aggregating
   frequency across jobs will need a normalisation step, which is not part of
   this policy.
