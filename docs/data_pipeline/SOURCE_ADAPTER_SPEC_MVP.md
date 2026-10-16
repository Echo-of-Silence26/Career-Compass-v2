# Source Adapter Specification

Status: Draft framework v0.1
Created: 2026-08-16
Updated: 2026-08-31 — LinkedIn un-parked via ADR-017; Indeed MCP connector
superseded by an Apify actor via ADR-018
Applies to: Indeed Apify actor (§2, active), Indeed MCP connector (§3,
superseded per ADR-018), LinkedIn Apify actor (§4, active), LinkedIn Chrome
Extension (§5, parked/superseded per ADR-017)

## 1. Common Adapter Contract

Every adapter emits the same immutable `SourceRecord` contract and must not
perform Candidate Profile matching, Capability Fit filtering, or application
recommendation.

Required common output:

```text
source_record_id
source
source_job_id
source_url
resolved_url
collection_run_id
sourcing_config_version
source_config_id
query_group_id
query_id
query_text_or_parameters
captured_at
adapter_version
parser_version
capture_method
raw_title
raw_company
raw_location
raw_description
raw_publication_date
raw_job_status
raw_work_mode
raw_payload_reference
content_hash
collection_status
parser_warnings[]
error_code
```

`result_position` (rank of the job within a single `search_jobs` call's
result list) was dropped from this contract on 2026-08-30 — decided not
useful enough to justify capturing.

Common behavioral requirements:

- immutable raw evidence and versioned corrections;
- idempotent retry;
- explicit Partial/Failed outcomes;
- no silent deletion of suspected duplicates;
- no storage of credentials or browser session secrets;
- preservation of source wording and date precision;
- adapter/parser versions on every record.

### Physical storage layout (raw capture)

Resolves the "Missing P0: machine-readable `RawJobRecord` schema and physical
JSONL layout" gap noted in `MVP_WORKFLOW_STAGE_CONTRACT_MAP.md` row 2, per
ADR-016's JSONL-only persistence decision.

- One file per source: `data/raw/source_records/{source}.jsonl`, e.g.
  `data/raw/source_records/indeed.jsonl`,
  `data/raw/source_records/linkedin.jsonl`. Not one file per
  `collection_run_id` — pre-extraction deduplication (workflow map stage 3)
  looks up `source + source_job_id` across all prior runs, so keeping one
  continuously-appended file per source keeps that lookup a single-file scan
  instead of a multi-file glob.
- Append-only, one line per capture: each line is exactly one `RawJobRecord` —
  the physical, on-disk form of the common `SourceRecord` contract above,
  serialized as one JSON object. A line is never rewritten or deleted; a
  changed posting produces a new line with a new `content_hash`, not an edit
  to the prior line (matches the "immutable raw evidence and versioned
  corrections" rule above and ADR-016).
- `raw_payload` field: in addition to the named `SourceRecord` fields, each
  line carries a `raw_payload` object holding the adapter's full, unmodified
  source response (the complete Apify dataset item, or the complete Indeed
  `get_job_details` markdown blob). Named fields are the common contract's
  narrow, cross-source-comparable projection; `raw_payload` is the safety net
  so a field observed in probing but not yet promoted to the common contract
  (e.g. LinkedIn's `seniorityLevel`, `employmentType`, `applicantsCount`) is
  never silently discarded.
- Gitignored under `data/raw/` (already excluded — see `.gitignore`); never
  committed. Redacted single-sample fixtures for documentation live separately
  under `data/private/fixtures/{source}/` (also gitignored).
- Identity index for dedup: the MVP scans the source's JSONL file directly
  (`JOB_SCHEMA_MVP.md` MVP Processing Rules already specifies
  `source + source_job_id` as the primary key); a separate in-memory or file
  index is an optimization, not a contract requirement, at MVP volume.

## 2. Indeed Apify Adapter

Status: Active for MVP (adopted 2026-08-31, ADR-018,
replacing the MCP connector adapter below in §3)

### Connector probe (2026-08-31)

A read-only probe ran the Apify Store actor `borderline/indeed-scraper` (build
`default`) via the REST API / `apify-client` Python SDK, using the same
gitignored-`.env` Apify token as the LinkedIn adapter (§4). Chosen from
several `PAY_PER_EVENT` Indeed actors on the Apify Store after explicitly
ruling out `curious_coder/indeed-scraper` (flat $20/month rental, no
per-result option). Input: `country: "de"`, `query: "Customer Success
Manager"`, `location: "Munich"`, `maxRows: 3`. Returned 3 live samples
(Workday "Executive Assistant"; Quantum-Systems "Returns Manager (m/f/d)";
TikTok "FMCG Account Manager"), saved unredacted to
`data/private/fixtures/indeed_apify/apify_probe_raw_2026-08-31.json`
(gitignored, not committed). Cost: pay-per-result, $0.005/dataset item; the
run self-aborted after reaching Apify's default per-run cost cap ($0.02),
having already returned all 3 requested items by then.

**Single-call discovery + detail**, same collapse as the LinkedIn Apify
adapter (§4) and unlike the two-call Indeed MCP connector (§3): one call
returns full job detail directly, no separate `get_job_details`-equivalent
step.

**Materially richer raw evidence than the MCP connector** — see ADR-018 for
the full comparison. Most notably: `jobKey` is Indeed's real job key (not a
per-session synthetic placeholder), `jobUrl` is already the canonical
`indeed.com/viewjob?jk=...` form (no shortlink, no redirect resolution),
`location` is a structured object, and `expired` / `isRemote` boolean fields
exist where the MCP connector had no status or work-mode signal at all.

### Mapping framework

| Common field | Indeed (Apify) field/path | Status / note |
|---|---|---|
| `source_job_id` | `jobKey` | **Verified present, all 3 samples.** Indeed's real job key (e.g. `ccbcbe954c79f2db`) — the same identifier the MCP-connector adapter (§3) needed a raw-HTTP redirect resolution to recover. |
| `source_url` / `resolved_url` | `jobUrl` | Verified present in canonical form already: `https://www.indeed.com/viewjob?jk={jobKey}`. No redirect resolution needed — collapses what was two separate common-contract fields into one directly-observed value for this adapter. |
| `raw_title` | `title` | Verified present, clean string. |
| `raw_company` | `companyName` | Verified present, clean string. Additional company fields also returned (`companyUrl`, `companyNumEmployees`, `companyRevenue`, `companyDescription`, `companyFounded`, `companyCeo`) — same "no home in the common contract yet, preserved via `raw_payload`" treatment as LinkedIn's company fields (§4). |
| `raw_location` | `location.formattedAddressLong` (or the structured object directly) | Verified present as a **structured object** (`city`, `postalCode`, `country`, `countryCode`, `latitude`, `longitude`) — no city/country-split parsing needed, unlike both the MCP connector and the LinkedIn actor. |
| `raw_description` | `descriptionText` | Verified present and looked complete in all 3 samples. `descriptionHtml` also returned; same convention as LinkedIn — persist `descriptionText` as `raw_description`, keep `descriptionHtml` in `raw_payload` only. |
| `raw_publication_date` | `datePublished` | Verified present as an ISO calendar date (e.g. `"2026-08-25"`) — matches the LinkedIn actor's precision, better than the MCP connector's formatted text. An `age` relative string (e.g. `"6 days ago"`) is also returned, redundant with `datePublished`. |
| `raw_job_status` | `expired` | **New — not available from either the MCP connector or the LinkedIn actor.** A boolean field. All 3 samples returned `expired: false`; no confirmed-`true` (closed) sample has been observed yet, so correctness on an actually-closed posting is unverified. |
| `raw_work_mode` | `isRemote` | **New — not available from either prior adapter.** A boolean field. All 3 samples returned `false`. Binary only (Remote vs. not) — does not distinguish Hybrid from On-site the way the common contract's `Remote/Hybrid/OnSite/Unknown` enum wants; mapping `isRemote: true` → `Remote` and `false` → needs a separate signal (or `Unknown`) to pick between Hybrid/On-site is still open. |

Fields returned by the actor with no home in the common contract yet
(`jobType`, `occupation`, `attributes`, `benefits`, `salary`, `rating`,
`contacts`, `emails`, `source`, `locale`, `language`, `isSponsored`, all
`company*` fields): preserved verbatim in each raw record's `raw_payload`
(§1), not dropped. `salary` was an empty object (`{}`) in all 3 samples —
untested whether that is common for this search or a general limitation.

### Partial / closed / access-restricted / retry behavior

Not yet probed. Only 3 successful, non-edge-case samples exist. No
closed/expired-confirmed, access-restricted, or invalid-input case has been
run against this actor yet.

### Open implementation questions

- confirm `expired` actually flips to `true` on a genuinely closed posting
  before trusting it as the `raw_job_status` signal — untested, all 3 samples
  were open;
- resolve the `isRemote` boolean's Hybrid-vs-On-site ambiguity against the
  common contract's four-value `work_mode` enum;
- pin the actor build explicitly (probe used `default`, which tracks the
  latest published version) once the mapping above is trusted, same rationale
  as the LinkedIn adapter's open question (§4);
- confirm `descriptionText` full-vs-preview behavior across more samples and
  search-filter combinations (`jobType`, `level`, `fromDays`, etc.);
- rate limits, retry/backoff, and the actor's own error taxonomy are
  unobserved — no failure case has been triggered yet;
- Apify's per-run default cost cap ($0.02, observed here) needs an explicit
  policy once real runs scrape more than a handful of jobs — either raise it
  deliberately per run or size `maxRows` to stay under it.

## 3. Indeed MCP Connector Adapter

Status: Superseded for MVP by the Indeed Apify Adapter above (§2, ADR-018,
2026-08-31) — not required now that a structured, non-Cowork-dependent Indeed
capture path exists. Design and probe history kept intact below for
reference; the redirect-resolution technique documented here remains the only
way to recover identity from this connector if it is ever needed again.

### Connector probe (2026-08-16)

A read-only capability probe was run against the only currently reachable
Indeed integration: the Claude-side MCP tool pair
`mcp__claude_ai_Indeed__search_jobs` and `mcp__claude_ai_Indeed__get_job_details`.
No crawler was built and no historical Excel was modified. One live sample
(IDnow, "Head of CSM (f/m/d)", Munich) was captured and redacted to
`data/private/fixtures/indeed/get_job_details_idnow_headofcsm_2026-08-16.json`
(gitignored via `data/private/`, not committed). No cookies, tokens, or
account/session data exist in this connector's output to begin with, so
nothing of that kind was captured or needed redaction beyond stripping
click-tracking query parameters from one intermediate redirect URL.

**This is not a licensed Indeed API.** There is no known API product,
endpoint, or authentication scheme behind it — `search_jobs` /
`get_job_details` are the entire interface, and `credential_reference:
INDEED_API_CREDENTIAL` in the source config does not correspond to anything
observed being used. Treat "Indeed API Adapter" in this document as shorthand
for "the Indeed MCP connector" until/unless a real API is identified.

**Discovery vs. Detail Capture:** the connector does both, but as two
separate calls with no shared identity between them beyond a
per-call-session placeholder:
- `search_jobs(search, location, country_code)` → Discovery. Returns a
  markdown-formatted list of job stubs (title, a synthetic `Job Id` like
  `JOBSEARCH_1170`, company, location, posted date, a `to.indeed.com` short
  link). No pagination/cursor parameter is exposed to the caller.
- `get_job_details(job_id)` → Detail Capture. Input is that same
  connector-issued placeholder `job_id`, **not** a URL and **not** Indeed's
  own job key. It was not confirmed to be valid outside the search response
  that produced it (untested: whether a `JOBSEARCH_1170`-style ID from one
  session works in another, or after time has passed). It returns one
  markdown text blob containing title, company, location, posted date, job
  type, compensation, and the full description body.

Both calls return unstructured markdown strings (a `result` field of prose),
not structured JSON — a parser must extract fields from the markdown, which
is itself a source of parser fragility not covered by the original
"field/path" framing below.

### Mapping framework (updated from probe)

| Common field | Indeed field/path | Status / note |
|---|---|---|
| `source_job_id` | *(none)* | **Not available from the connector directly, but recoverable out-of-band in 3/3 samples so far — method matters.** The real Indeed job key (`jk=...`) is always present as a plain query parameter in the `Location` header of the `to.indeed.com` short link's first redirect (`to.indeed.com/{code}` → `indeed.com/{rc\|uie\|pagead}/clk?...&jk=...`), regardless of which of the 3 observed redirect path shapes it uses. **Critical implementation detail:** this must be read via a raw HTTP request (e.g. `curl -D -`) that returns the unmodified `Location` header. An AI-summarizing fetch tool (this probe initially used `WebFetch`) truncated 2 of 3 of these URLs before reaching the `jk=` parameter — because the URL also carries a long opaque ad-tracking blob (`e=` or `ad=`) ahead of it — and wrongly appeared to show no recoverable key. That was a tool artifact, corrected in fixture round 3 (`get_job_details_probe_round3_correction_2026-08-16.json`); do not repeat the round-2 mistake of concluding "unresolvable" from a summarizing tool's truncated output. |
| `source_url` | `result: 'View Job URL'` | Present, but is a `to.indeed.com` short link. Confirmed unreliable in prior audits — short links can 404, rotate, or resolve to a *different* company's posting ([[indeed-shortlink-scramble]] memory). Company match must be re-verified after resolving, every time, before trusting a resolved link. |
| `resolved_url` | *(none)* | **Not available from the connector directly, but recoverable in 3/3 samples so far** by the same raw-HTTP redirect resolution as `source_job_id` above. Canonical form observed: `https://www.indeed.com/viewjob?jk={jk}`, confirmed reachable and company-matched for all 3 samples. |
| `raw_title` | `result: 'Job Title'` | Verified present in one sample. |
| `raw_company` | `result: 'Company'` | Verified present; matched the resolved live page in the one sample checked. |
| `raw_location` | `result: 'Location'` | Verified present, but as a single free-text string (e.g. `"München"`) — no separate city/country fields, so the Job Schema's `city`/`country` split must happen in the parser, not the connector. |
| `raw_description` | `result:` free text after the header block | Present and looked complete for this one sample (full JD including responsibilities, requirements, perks). Full-vs-preview guarantee is **not yet proven** — needs more samples, including a case suspected to be preview-only, before this can be marked Verified. |
| `raw_publication_date` | `result: 'Posted on'` | Present, but only as a coarse formatted date (`"August 10, 2026"`) — no time, and no marker distinguishing an exact vs. relative source date, which Policy §4 requires preserving. |
| `raw_job_status` | *(none)* | **Not available from the connector at all** — no field or text signals open/closed/expired. The one sample was confirmed open only by manually resolving the redirect chain and inspecting the live Indeed page outside the tool. An adapter that needs open/closed detection cannot get it from `get_job_details` alone. |
| `raw_work_mode` | *(none)* | **Not available as a structured field.** Only weakly inferable from free-text benefits copy (e.g. "remote work" mentioned in a perks paragraph), which is not a reliable Remote/Hybrid/OnSite signal and should not be parsed as one without much more validation. |

### Result cap and repeat-query behavior (2026-08-30)

Every observed `search_jobs` call across all probes so far has returned
exactly 10 results, with no pagination/cursor parameter exposed in the tool
schema. Whether 10 is a hard per-call cap or the true total was previously
unconfirmed.

New evidence: the identical call (`search: "Growth Manager"`,
`location: "Munich"`, `country_code: "DE"`) was issued twice in immediate
succession. 9 of the 10 returned jobs were the same postings both times
(same company/title/posted-date, new synthetic `JOBSEARCH_xxx` IDs each
call, consistent with those IDs being per-call and not stable). The 10th
slot differed: the first call's 10th result (SIXT, "Senior Sports
Partnerships & Growth Manager") was absent from the second call, replaced by
a job not present in the first call at all (Mueller, "Sales Manager DACH").

This means the true underlying match count for at least this one query
likely exceeds 10 — a fixed 10-item result set could not produce a genuinely
new 10th job on repeat. It also means **repeating an identical query and
taking the union of results is a viable, empirically-supported way to
recover some of the jobs truncated by the 10-result cap**, though it is not
true pagination: there is no control over which/how many additional results
surface per repeat, the total remains Unknown, and this one sample only
gained 1 new job per repeat (not a large or guaranteed yield).

### Partial / closed / access-restricted / retry behavior

- **Partial:** not yet observed or testable from this connector — since it
  has no structured "preview vs full" signal, an adapter cannot currently
  distinguish a partial description from a full one except by manual
  inspection. Treat every capture as `description_status: RequiresFixtureValidation`
  until a confirmed-partial sample exists, not as `Full` by default.
- **Closed:** still not directly observed as a positive case (no confirmed-
  closed sample yet). A 4-month-old posting (CodeSphere, posted 2026-04-21,
  queried 2026-08-16) returned full `get_job_details` content with no
  closure signal, and once correctly resolved via raw HTTP (see
  `source_job_id` row above; the earlier "unresolvable" read was a tool
  artifact, corrected in fixture round 3) turned out to still be open/active
  on the live Indeed page. So `get_job_details` genuinely had no stale
  content in this case — but the method to check is still "resolve `jk` via
  raw HTTP and inspect the live page," since `get_job_details` itself never
  carries a status field. An adapter should still not assume a posting is
  open just because `get_job_details` returned content; it must perform the
  live-page check for any job it intends to persist as open. Do not infer
  "closed" from an empty/short description — that is indistinguishable from
  a parser miss.
- **Access restricted:** none encountered. Indeed prompts a visitor to
  create an Indeed account before proceeding to a company's own external
  application page; this is a normal Indeed apply-flow gate, not a wall
  blocking access to the job posting or description, and no login was
  attempted or needed to read the posting.
- **Retry:** an invalid/unknown `job_id` (`NOT_A_REAL_ID_9999`) returned a
  single generic opaque error string ("There was an error getting job
  details. Please try again later.") with no structured code and no
  explicit retryable/terminal signal. This does not yet map to any code in
  the shared error framework (section 4) — treat it as `UNKNOWN` until more
  failure modes (rate limiting, closed job, network error) are observed.
  No rate-limit response was triggered by this small probe.

### Job_id behavior (resolved this round)

- The connector-issued placeholder `job_id` (e.g. `JOBSEARCH_1170`) **was
  confirmed valid across multiple separate tool calls within the same
  session**, including calls made in a later conversation turn than the
  `search_jobs` call that produced it. It is not single-use.
- Still untested: validity in a brand-new session, or after a long time
  gap — not observable within one conversation.

### Open implementation questions

- whether the connector's placeholder `job_id` remains valid across
  sessions or after a long time gap — untested within a single probe;
- whether `jk` is *always* present as a plain query parameter across every
  redirect shape Indeed uses, or whether the 3 shapes seen so far (`rc/clk`,
  `uie/clk`, `pagead/clk`) are not exhaustive — only 3 samples tested;
- whether resolving every posting's short link at crawl scale (one raw HTTP
  request per job, every run) behaves differently under Cloudflare's
  bot-management than the handful of one-off manual checks done here — a
  `__cf_bm` anti-bot cookie was observed being set on every redirect
  response; rate limiting or challenge pages at volume are untested;
- full-description-versus-preview behavior across more than one sample;
- closed/expired-job detection — no confirmed-closed sample exists yet, so
  the live-page closure marker itself hasn't actually been observed, only
  inferred as necessary since `get_job_details` carries no status field;
- work-mode detection, since `get_job_details` carries no structured field;
- rate limits and retry/backoff requirements — no rate limit was hit in
  this small probe;
- pagination/cursor and total-result-count behavior for `search_jobs`
  (partially addressed 2026-08-30: repeat calls are not identical, see
  "Result cap and repeat-query behavior" above — but yield size, ceiling,
  and reliability of repeat-and-union are still unmeasured);
- source ID stability across reposts;
- what, if anything, `credential_reference: INDEED_API_CREDENTIAL` in the
  source config actually refers to, given no API credential was used or
  needed by this connector;
- full error-code taxonomy and retryability — only the invalid-`job_id`
  case was observed, and it returned one generic, unclassified error string.

## 4. LinkedIn Apify Adapter

Status: Active for MVP (un-parked 2026-08-31, ADR-017)

### Connector probe (2026-08-31)

A read-only probe ran the Apify Store actor
`curious_coder/linkedin-jobs-scraper` (build `latest`, not yet pinned — see
Open implementation questions) via the REST API / `apify-client` Python SDK,
authenticated with a personal Apify API token stored in a gitignored `.env`.
One call (`urls: ["https://www.linkedin.com/jobs/search/?keywords=Customer%20Success%20Manager&location=Munich%2C%20Germany"]`,
`limitPerSource: 3`, `scrapeCompany: true`) returned 2 live samples (Heidi
Health, "Customer Success Manager, DACH"; Mercura, "Customer Success
Manager"), saved unredacted to
`data/private/fixtures/linkedin/apify_probe_raw_2026-08-31.json` (gitignored,
not committed). Cost: pay-per-result, ~$0.001–0.002 per dataset item plus a
negligible per-run start fee (`pricingInfos` on the actor).

**Single-call discovery + detail:** unlike the Indeed connector's two-call
split (`search_jobs` then `get_job_details`, §3), this actor returns full job
detail — including company profile fields when `scrapeCompany: true` — in the
same call/dataset item that performs discovery. There is no separate
Discovery-vs-Detail-Capture step for this adapter; workflow map stages 1–2
collapse into one call for LinkedIn.

**Run-log / dataset-count mismatch (unexplained):** the actor's own log
reported "Scraped 3 jobs (3 from this search)" but the fetched dataset
contained only 2 items. Not yet root-caused — candidates include a
company-enrichment failure silently dropping one item, or an async
dataset-write race despite the run status being `SUCCEEDED`. Treat
`records_captured` counts from this adapter as provisional until a larger
probe either reproduces or rules this out; do not assume the actor's log
count and the dataset item count always agree.

### Mapping framework

| Common field | LinkedIn (Apify) field/path | Status / note |
|---|---|---|
| `source_job_id` | `id` | **Verified present, both samples.** A real, stable LinkedIn platform job ID (e.g. `4457399938`) — unlike Indeed's per-session synthetic `JOBSEARCH_xxxx` placeholder, this is LinkedIn's own numeric job identifier embedded directly in `link`. |
| `source_url` | `link` | Verified present. A direct canonical `https://{locale}.linkedin.com/jobs/view/{slug}-{id}?...` URL — **no redirect-resolution step needed**, unlike Indeed's `to.indeed.com` short link ([[indeed-shortlink-scramble]] does not apply here). Carries search-session tracking query params (`position`, `pageNum`, `refId`, `trackingId`) that are not part of the job's identity. |
| `resolved_url` | *(derived)* | Not returned separately by the actor; the adapter should derive it by stripping the tracking query params from `link` down to `https://{locale}.linkedin.com/jobs/view/{slug}-{id}`. Untested whether the `{locale}` subdomain (`de.linkedin.com` in both samples) is stable or search-region-dependent. |
| `raw_title` | `title` | Verified present, clean string (no markdown parsing needed, unlike Indeed). |
| `raw_company` | `companyName` | Verified present, clean string. With `scrapeCompany: true`, additional company fields are also returned (`companyLinkedinUrl`, `companyWebsite`, `companyDescription`, `companyEmployeesCount`, `companyAddress`) — none map to the current common contract; captured via `raw_payload` (see §1 Physical storage layout) pending a possible future `Company` entity. |
| `raw_location` | `location` | Verified present, but a single free-text string (e.g. `"Munich, Bavaria, Germany"`) — same city/country-split-in-parser situation as Indeed. |
| `raw_description` | `descriptionText` | Verified present and looked complete in both samples. The actor also returns `descriptionHtml` (formatted); MVP should persist `descriptionText` as `raw_description` to match Indeed's plain-text convention and keep `descriptionHtml` in `raw_payload` only. Full-vs-preview guarantee is unproven beyond these 2 samples, same caveat as Indeed. |
| `raw_publication_date` | `postedAt` | Verified present as an ISO calendar date (`"2026-08-21"`) — more precise than Indeed's formatted text (`"August 10, 2026"`), but still date-only, no time component. |
| `raw_job_status` | *(none)* | **Not available from the actor at all**, same gap as Indeed — no field signals open/closed/expired in either sample. |
| `raw_work_mode` | *(none observed)* | Not present as a structured field in either sample. LinkedIn's own search UI exposes Remote/Hybrid/On-site as a filter, so a structured value may exist under some input combination not yet probed — untested. |

Fields returned by the actor with no home in the common contract yet
(`applicantsCount`, `benefits`, `salary`, `applyUrl`, `seniorityLevel`,
`employmentType`, `jobFunction`, `industries`, `trackingId`, `refId`,
`inputUrl`, all `company*` fields): preserved verbatim in each raw record's
`raw_payload` (§1), not dropped. `salary` and `applyUrl` were empty strings in
both samples — untested whether that is "usually empty for this search" or a
general actor limitation.

### Partial / closed / access-restricted / retry behavior

Not yet probed. Only 2 successful, non-edge-case samples exist. Unlike the
Indeed probe, no invalid-input, closed-job, or access-restricted case has
been run against this actor yet.

### Open implementation questions

- pin `defaultRunOptions.build` to a specific version instead of `latest`
  once the mapping above is trusted, so an upstream actor update cannot
  silently change output shape;
- root-cause the run-log-vs-dataset-count mismatch (3 scraped vs. 2 returned)
  before relying on this adapter's counters for reconciliation
  (`COLLECTION_RUN_SPEC.md` §4/§7 counters);
- confirm `descriptionText` full-vs-preview behavior and `raw_job_status` /
  `raw_work_mode` structured availability across more samples and more
  input-filter combinations (`datePosted`, `under10Applicants`, etc.);
- confirm whether the `{locale}` subdomain in `link` is stable per company or
  varies by search region, since `resolved_url` derivation depends on it;
- `limitPerSource` and `splitByLocation` (bypasses LinkedIn's ~1000-job cap
  per search by splitting across cities) are unexplored beyond the
  small probe value used here — result-cap and pagination-equivalent
  behavior at larger volumes is untested;
- rate limits, retry/backoff, and the actor's own error taxonomy are
  unobserved — no failure case has been triggered yet.

## 5. LinkedIn Chrome Extension Adapter

Status: Parked for MVP (2026-08-20); superseded for MVP purposes by the
LinkedIn Apify Adapter above (§4, ADR-017, 2026-08-31) — not required now that
a non-interactive, non-browser LinkedIn capture path exists. Design kept
intact below in case a logged-in-account capture need (skills, applicant
insights, Apply URLs — noted as available only via a *different*,
logged-in-account Apify actor, not this one) reopens it post-MVP.

### Confirmed

- User-triggered capture; no autonomous background crawling in v0.1.
- Support LinkedIn search-result and job-detail contexts.
- Preserve the active search/filter context with captured records.
- Treat login walls, CAPTCHA/access restrictions, closed jobs, and preview-only
  descriptions as explicit outcomes; do not bypass platform controls.
- Do not collect candidate, recruiter, connection, cookie, token, or session
  credential data.

### Proposed capture actions

| Action | Status | Intended result |
|---|---|---|
| Capture current job detail | Partial | One full SourceRecord |
| Capture visible search results | Partial | Discovery records; detail completion may remain pending |
| Mark already captured results | Open | Requires local/backend identity lookup |
| Retry queued submission | Open | Must remain idempotent |

### Mapping framework

| Common field | LinkedIn page evidence | Status / note |
|---|---|---|
| `source_job_id` | job URL/DOM identifier | Open selector and stability test |
| `source_url` | current/result link | Partial |
| `resolved_url` | canonical detail URL | Open |
| `raw_title` | detail/search card | Open selector |
| `raw_company` | detail/search card | Open selector |
| `raw_location` | detail page | Open selector |
| `raw_description` | expanded job description | Must detect truncated/preview text |
| `raw_publication_date` | exact or relative page text | Preserve precision |
| `raw_job_status` | apply/closed page state | Open state mapping |
| `raw_work_mode` | page field/text | Open state mapping |
| query/filter context | search URL + visible filters | Open serialization |

### Open implementation questions

- Manifest version and minimum browser permissions;
- content-script selectors and DOM-change detection;
- detail-opening/description-expansion interaction;
- one-job versus visible-results UX for MVP;
- local queue storage, authentication to backend, and retry behavior;
- duplicate feedback shown to the user;
- permission and retention review;
- test fixtures for search, detail, closed, login-wall, and truncated pages.

## 6. Error and Warning Framework

Proposed shared error families:

```text
AUTH_REQUIRED
ACCESS_RESTRICTED
RATE_LIMITED
NETWORK_ERROR
PAGE_NOT_JOB
JOB_CLOSED
DESCRIPTION_MISSING
DESCRIPTION_PARTIAL
PARSER_MISMATCH
SOURCE_ID_MISSING
SUBMISSION_FAILED
UNKNOWN
```

Each code still needs a source-specific mapping and a `retryable` flag. A
missing non-critical field should normally be a warning, not a failed capture.

## 7. Adapter Definition of Done

- [ ] Common contract mapping is complete.
- [ ] Full and partial JD behavior is tested.
- [ ] Query/config provenance survives capture.
- [ ] Rerunning the same observation is idempotent.
- [ ] Updated content produces a version rather than overwriting raw evidence.
- [ ] Run counters reconcile with emitted SourceRecords.
- [ ] Errors are visible and classified as retryable or terminal.
- [ ] No secret/session data is persisted.
