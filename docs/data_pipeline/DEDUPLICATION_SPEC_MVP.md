# Deduplication Specification

Status: Frozen v0.1
Created: 2026-08-31
Frozen: 2026-09-01
Owning workflow stage: [`MVP_WORKFLOW_STAGE_CONTRACT_MAP.md`](MVP_WORKFLOW_STAGE_CONTRACT_MAP.md)
row 3 (Layer 1) and a new post-extraction step this spec adds (Layer 2)
Extends: [`DATA_PIPELINE_MVP_SPEC.md`](DATA_PIPELINE_MVP_SPEC.md) §4.2;
[`JOB_SCHEMA_MVP.md`](JOB_SCHEMA_MVP.md) MVP Processing
Rules; [`SOURCE_ADAPTER_SPEC_MVP.md`](SOURCE_ADAPTER_SPEC_MVP.md) §1 Identity
index; the `identity:` block in
[`sourcing-v0.1.yaml`](../../config/sourcing/sourcing-v0.1.yaml)
(this spec is the executable design behind that config's
`cross_source_rule: CreateDuplicateCandidate`, which had no implementation
until now)

## 1. Scope: Two Dedup Layers, Not One

Now that both Indeed and LinkedIn are active sources, "deduplicate" covers
two mechanically different problems that must not be collapsed into one step:

| | Layer 1 — Intra-source identity dedup | Layer 2 — Cross-source candidate matching |
|---|---|---|
| Question answered | "Have I already captured this exact posting from this source?" | "Are these two postings from different sources probably the same job?" |
| Identity available | Real source-issued ID (`jobKey` / `id`) in almost every case | None — no shared ID exists between Indeed and LinkedIn |
| Runs | Stage 3, before LLM extraction | After stage 4 extraction, on canonical `Job` fields |
| Confidence | Deterministic, exact | Heuristic, approximate |
| Effect on the pipeline | Skips extraction/HD/Fit entirely for the duplicate | Strong tier: skips stages 5+ (eligibility/HD/Fit) for the later-published record. Weak tier: never skips anything — review-time signal only |
| Status | **Required for MVP**, not yet implemented (`RawJobDeduplicator`, build tracker stage 3) | **Post-MVP** per `DATA_PIPELINE_MVP_SPEC.md`'s "cross-source deduplication... remain post-MVP" line — this spec designs it now so the shape is agreed, not to move up its build order |

## 2. Layer 1 — Intra-Source Identity Dedup

Formalizes what `DATA_PIPELINE_MVP_SPEC.md` §4.2 and
`JOB_SCHEMA_MVP.md`'s MVP Processing Rules already accepted, into
an executable spec for `RawJobDeduplicator`.

### 2.1 Identity resolution

1. **Primary identity:** `source + source_job_id` (`jobKey` for Indeed,
   `id` for LinkedIn — both verified present on every probed sample, see
   `SOURCE_ADAPTER_SPEC_MVP.md` §2/§4).
2. **Fallback identity:** when `source_job_id` is unavailable, use
   `source + resolved_url`.
3. If neither is available, the record cannot be identity-matched — treat as
   `new` and route to §2.4 (weak-signal candidate flagging), never silently
   drop it.

### 2.2 Lookup scope

Scan only the same source's own `data/raw/source_records/{source}.jsonl`
(per `SOURCE_ADAPTER_SPEC_MVP.md` §1 — this is why the file is one
continuously-appended file per source, not per run: a single-file scan, no
cross-file glob, and by construction never compares across sources). Layer 1
is intentionally blind to the other source's file.

### 2.3 Outcome classification

| Outcome | Condition | Action |
|---|---|---|
| `new` | No prior record with this identity in this source's file | Continue to stage 4 extraction |
| `duplicate_unchanged` | Identity exists and the new capture's `content_hash` matches the prior one | Record the outcome for stage 10 reconciliation; skip extraction, HD, and Fit entirely |
| `changed` | Identity exists but `content_hash` differs | Continue to stage 4 extraction; the resulting `Job` record is updated in place (no historical version retained, per `JOB_SCHEMA_MVP.md`) |

`content_hash` is computed by `pipeline/source_record.py::compute_content_hash`
(sha256 over title/company/location/description/publication_date) — already
implemented and exercised by both adapters.

### 2.4 Weak-signal fallback within the same source

When `source_job_id` is missing (only observed for the superseded Indeed MCP
connector so far, not either current Apify adapter) *and* `resolved_url`
disagrees or is also missing, do not attempt to auto-match on
company/title/location. Route it through the same candidate mechanism as
Layer 2 (§3) rather than defining a second, separate "weak dedup" path —
one mechanism, reused, per §4's data contract. This unifies what the old
`indeed-de-v0.1.yaml` called `CreateDuplicateCandidateDoNotAutoMerge`
with Layer 2 below instead of leaving it as a disconnected rule.

## 3. Layer 2 — Cross-Source Candidate Matching

### 3.1 Why this runs after extraction, not on raw records

Rejected: matching on raw `SourceRecord` fields, before extraction, to also
save extraction cost on the probable duplicate. Two reasons this is not the
MVP design:

- **Raw fields aren't safely comparable across sources yet.** Indeed's
  `raw_location` is a structured object (`city`, `postalCode`, `country`,
  ...); LinkedIn's is a single free-text string (`"Munich, Bavaria,
  Germany"`). The canonical `Job` schema already does this
  city/country split during extraction — reusing it is simpler and more
  reliable than re-deriving the same normalization twice, once per source,
  ahead of extraction.
- **Skipping extraction on a suspected duplicate risks silent record loss.**
  Two concurrent, genuinely distinct postings can share company and title
  (e.g. a company running two parallel "Account Manager" reqs). Every other
  identity rule in this pipeline treats an unconfirmed match as
  `CreateDuplicateCandidate`, never as `Skip` (`SOURCE_ADAPTER_SPEC_MVP.md`
  §1's "no silent deletion of suspected duplicates"). Matching pre-extraction
  would only be justified if it *skipped* work; since Layer 2 must not skip
  *extraction* anyway (§3.4), running it after extraction costs nothing extra
  and gets cleaner input.

  §3.4 does allow a Strong-tier match to skip stages 5+ for the
  later-published record, but only after extraction has already produced a
  full `Job` record on both sides — so this bullet's concurrent-distinct-
  postings risk is narrowed (both records keep their full content; at most
  one loses eligibility/HD/Fit processing) rather than eliminated. See §3.4's
  tie-break rule and §5.

### 3.2 Matching signal

All deterministic string normalization — **no embeddings, no LLM
similarity call.** This keeps the same "semantic dedup is post-MVP" boundary
`DATA_PIPELINE_MVP_SPEC.md` already draws; Layer 2 is post-MVP as a whole,
but if/when it is built it should not quietly reintroduce a semantic-matching
dependency through the back door.

- `normalized_company`: lowercase; trim whitespace; strip common
  legal-entity suffixes (`GmbH`, `AG`, `KG`, `Inc`, `LLC`, `Ltd`, `Co`, ...) —
  list starts small and grows from observed false negatives, not guessed
  exhaustively up front.
- `normalized_title`: lowercase; trim whitespace/punctuation; strip
  parenthetical diversity-notation suffixes (`(m/f/d)`, `(f/m/d)`, `(w/m/d)`)
  seen directly in the Indeed fixture sample ("Returns Manager (m/f/d)").
- `normalized_city`: lowercase city name, taken from the canonical `Job`
  schema's already-split `city` field (not re-parsed from raw text).
- `description_similarity` is explicitly **not part of v0.1 matching**. A
  deterministic token-overlap ratio may be evaluated in a future version,
  after real candidate pairs exist for threshold tuning; it must not change a
  Strong/Weak decision under this frozen version.

### 3.3 Match tiers

| Tier | Condition | Meaning |
|---|---|---|
| Strong candidate | `normalized_company` + `normalized_title` + `normalized_city` all match, including when both normalized cities are `remote` | High-confidence same posting |
| Weak candidate | `normalized_company` + `normalized_title` match, but cities differ, or either side's city is `Unknown` | Plausible same posting; location mismatch could be a parsing gap, a genuinely different office, or a Remote-vs-Hybrid labeling difference |
| No match | Anything else | Treated as two distinct jobs; no flag written |

`Remote` is an ordinary normalized city value for tiering: `Remote` ↔
`Remote` is a city match and may be Strong; `Remote` ↔ a concrete city is a
city mismatch and is Weak. `Unknown` never supplies the city agreement needed
for Strong, including `Unknown` ↔ `Unknown`.

Tiering is first computed pairwise, then checked for cardinality. A Strong
match may auto-resolve only when it is strictly one-to-one: each record has
exactly one Strong candidate and those records point to each other. If any
record participates in more than one Strong pair, every Strong pair in that
ambiguous candidate group is downgraded to Weak. All records proceed through
stages 5–8 and all candidate relationships are retained for human review.

### 3.4 Action: never merge, never silently drop; tier decides whether it skips

This is where the config's existing `cross_source_rule:
CreateDuplicateCandidate` (`sourcing-v0.1.yaml`) gets an actual
mechanism. Both matched `Job` records always get a mutual entry in their
`duplicate_candidates` lists (see §4), containing the other record's
`job_id`, `source_url`, match basis, and confidence — never a merge, never a
deletion of either record's content. What differs by tier is whether the
pipeline is also allowed to skip stages 5+ on its own:

**Strictly one-to-one Strong candidate — pipeline auto-skips the later posting**

- Compare `published_at` on both records. When they're non-null and unequal,
  the record with the earlier `published_at` proceeds normally
  (`duplicate_status: AutoKept`); the one with the later `published_at` is
  excluded from stages 5–8 and gets `duplicate_status: AutoSkipped`. The
  two exception cases below (equal / missing) are handled separately.
- **Equal-timestamp tie-break:** if both sides have a non-null `published_at`
  and the two are equal, prefer Indeed — the Indeed record gets `AutoKept`,
  the LinkedIn record gets `AutoSkipped`. This is a fixed, deterministic
  source-priority rule (not a guess about which posting is actually older);
  revisit it if a source-preference reason emerges later.
- **Missing-date exception:** if either side's `published_at` is `null`,
  there is no basis at all to compare — do not guess and do not apply the
  Indeed tie-break. Treat the pair as a Weak candidate instead (flag only,
  both proceed, human resolves it in review).
- `AutoSkipped` is not a silent drop: the record keeps its full extracted
  content, still appears in the stage 11 Excel export (marked `AutoSkipped`,
  with its candidate URL linking to the surviving posting so the
  reviewer can check it on the other platform), and a human can override the
  auto-decision by setting `duplicate_status` to `ConfirmedDistinct` if the
  match turns out to be wrong (e.g. the "two parallel reqs" case from §3.1).

**Weak candidate — flag only, unchanged from the original design**

- Both jobs proceed through stages 5–8 independently and in full. Layer 2
  never causes a Weak-tier job to be skipped or excluded on its own.
- Both appear in the Excel human-review export (stage 11) with the match and
  candidate URLs visible, so a human can mark one
  `ConfirmedDuplicate` and the other `ConfirmedDistinct` (or leave both
  `Unreviewed`) — the human decision is what actually resolves the pair,
  matching this pipeline's existing rule that Excel review, not an automated
  step, owns duplicate/distinct calls for anything short of a Strong match.

## 4. Data Contract Additions

Applied to the canonical `Job` schema
(`JOB_SCHEMA_MVP.md`); listed here as the concrete fields this
spec needs:

```text
duplicate_candidates:                     # [] when no candidates; retains every relationship
  - job_id: string                         # matched Job
    source_url: string                     # cross-platform review link
    match_basis: enum                      # IntraSourceWeakFallback | CrossSourceStrong | CrossSourceWeak
    confidence: enum                       # Strong | Weak
duplicate_status: enum                    # Unreviewed | AutoKept | AutoSkipped | ConfirmedDuplicate | ConfirmedDistinct  (default: Unreviewed)
```

Candidate entries are deduplicated by `job_id` and stored in ascending
`job_id` order so output is deterministic. `duplicate_status` is set once by
the pipeline (`Unreviewed` for every Weak
match and every Strong match caught by the §3.4 tie-break exception;
`AutoKept` / `AutoSkipped` for a resolved Strong match) and can be
overwritten exactly once, by a human, during stage 11 review — either
confirming an `Unreviewed` pair (`ConfirmedDuplicate` / `ConfirmedDistinct`)
or overriding a pipeline mistake on an `AutoSkipped` record
(`ConfirmedDistinct`, which restores it to stages 5–8 on the next run).
`duplicate_candidates` is written by the pipeline and never edited by a
human, consistent with "immutable raw evidence" applied one layer up to
derived `Job` records.

## 5. Known Gaps Not Solved By This Spec

- Legal-suffix and title-suffix normalization lists above are starting
  points, not validated against a real sample set yet.
- A same-company repost under a *changed* title (e.g. "Account Manager" →
  "Senior Account Manager") will not match §3.3's tiers — a known miss, not
  claimed as solved.
- No feedback loop yet from a human's `ConfirmedDuplicate` call back into
  future runs (e.g. suppressing the pair automatically next time) — depends
  on the Excel review-import behavior, itself Missing P1
  (`MVP_WORKFLOW_STAGE_CONTRACT_MAP.md` row 11).
- Strong-tier auto-skip (§3.4) trades a small false-positive risk for less
  manual review volume: two genuinely distinct, concurrently open reqs at
  the same company/title/city (the "two parallel Account Manager reqs" case
  from §3.1) will be auto-skipped, not just flagged. Mitigated by keeping
  the skipped record's content and letting a human reverse it via
  `ConfirmedDistinct`, but not yet validated against a real sample of
  true/false Strong matches — revisit the `normalized_city` requirement (or
  add `description_similarity` as a required gate, not just a tie-nudge) if
  false positives show up in practice.
- Description similarity is outside frozen v0.1. A future version may add it
  only after its tokenization and thresholds are tuned against real candidate
  pairs and the versioned rule is updated explicitly.

## 6. Implementation Order

Layer 1 blocks stage 4 and is required before any end-to-end run — it should
be built now, alongside the still-`Not started` `RawJobDeduplicator` row in
the build tracker. Layer 2 depends on stage 4's extraction
output existing at all, so it cannot be built before Layer 1 regardless of
its own post-MVP priority.
