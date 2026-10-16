# Sourcing Policy

Status: Accepted v0.2
Created: 2026-08-16
Change (2026-08-30): active role family list updated — Marketing removed (no
standalone vocabulary was ever defined for it in §3; it is treated as a
growth lever, not a target role family), IT Project Management activated
(§3 vocabulary un-parked).
Change (2026-09-03): Customer Success archived from prospective collection;
IT Project Management deactivated; Product Manager / Product Owner activated.
Historical CSM baselines and experiments remain unchanged and available for
retrospective evaluation.
Scope: prospective collection for Growth and Product Management

## 1. Boundary

Sourcing discovers and preserves jobs; it does not perform Candidate Profile
matching, Capability Fit pre-screening, or application recommendation. Source
and query configuration may define the intended role family, but a collector
must not silently drop a result because its industry, skills, seniority, or
responsibilities appear to be a poor fit.

The active prospective role families are:

- Growth;
- Product Management (Product Manager and Product Owner).

Customer Success is archived: do not run new CSM queries. Its 88-record
historical baseline remains valid historical evidence and must not be deleted
or relabelled. IT Project Management is inactive for prospective sourcing.
Marketing is not sourced as its own target role family — it is a Growth
lever (see `Growth Marketing`, `Product Lead Growth` in the §3 Growth
vocabulary).

## 2. Geography, Language, and Work Mode

- Candidate base: Munich, Germany.
- Search German- and English-language postings.
- Fully remote: the employer's office may be anywhere in the world, provided
  the job explicitly permits working from Munich/Germany. `Remote` alone does
  not prove eligibility; country, region, time-zone, travel, and office-attendance
  restrictions must be preserved. Unclear cases are collected with remote
  eligibility marked `Unknown`.
- Hybrid and on-site: the office must be in Munich or within approximately 150
  km of Munich.

## 3. Search Vocabulary

Search vocabulary widens discovery and is not a matching rule.

### Product Management 

- Product Manager
- Product Owner
- Produktmanager
- Business Analyst



### Growth

- Growth Manager / Specialist / Associate
- Growth Marketing Manager
- Growth Operations Manager
- Growth Project Manager
- Business Growth Manager / Customer Growth Manager
- Lifecycle Marketing Manager / Lifecycle Manager
- Retention Manager / Customer Retention Manager
- CRM Manager / Engagement Manager
- Go-to-Market Manager / GTM Manager
- Revenue Operations Manager / Commercial Operations Manager
- Business Development Manager
- Growth Innovation Manager
- Growth Strategy Specialist / Associate
- New Business & Growth Manager
- Growth Operations Manager
- Product Lead Growth
- Growth Marketing
- Product Enablemeng Manager
- Produktmarketing Manager / Produktmarketing Spezialist



Do not include `Technical Project Manager` or `Technischer Projektmanager` in
this query group.

There are no include- or exclude-keyword rules in v0.1. Company and industry
are unrestricted at collection time. Seniority is not filtered by the
collector; it is evaluated under the versioned Hard Disqualifier policy.

## 4. Time Window and Open Status

- Initial Product Management backfill: collect every visible result within the
  source-supported initial window that is still open, with no business result
  cap. A technical spend guard is still mandatory.
- Incremental runs: collect new or changed jobs, normally daily.
- Daily runs use the narrowest supported source-side time filter before paid
  capture. Do not schedule a recurring wider backfill: it would pay again for
  already-seen results. Run a wider recovery window only after a recorded
  incomplete or failed run, accepting its explicit recovery cost.
- Do not impose a per-source or per-query result cap. A run must nevertheless
  record the number of results reported, scanned, captured, unchanged, failed,
  and left unscanned so that zero new jobs is distinguishable from an
  incomplete run.
- A job with no reliable publication date may be collected if it is confirmed
  open; preserve a null/unknown date and a parser warning.
- A closed job may be retained for discovery/audit provenance but does not
  enter the current assessment flow.

For a verified cross-source instance of the same opening, retain every raw
source publication date and set `first_published_at` to the earliest credible
date. `first_seen_at` remains the system's first observation time. Imprecise
source dates must retain their precision. A repost date is stored separately
and does not overwrite the original `first_published_at`.

## 5. Identity, Updates, and Reposts

- Same source job ID and same content hash: unchanged observation; update
  `last_seen_at` without creating an uncontrolled duplicate.
- Same source job ID and changed content hash: create a new job/source version.
- Different source ID with highly similar company, title, location, and JD:
  create a repost or cross-source duplicate candidate; do not auto-merge an
  uncertain case.
- Preserve immutable raw source records, source URLs, timestamps, and content
  hashes. A human decision never causes the collector to erase source history.

Human decision states are `Unreviewed`, `Rejected`, and `Applied`; there is no
`Skip` label. Only `Unreviewed` jobs enter the downstream human-review queue.
Reposts and updates do not automatically reopen `Rejected` or `Applied` jobs.
A new version may be reconsidered only after an explicit human reset to
`Unreviewed`.

## 6. Initial Source Adapters

- Use the Indeed and LinkedIn Apify adapters.
- Run Indeed and LinkedIn sequentially for the current low-volume workflow so
  source-level counts, failures, and spend remain easy to inspect. Parallelism
  may be enabled later if observed latency becomes material.
- Both adapters must emit the same source-record contract and preserve source,
  source job ID, original and resolved URL, query/configuration, collection run,
  raw fields, capture time, adapter/parser version, warnings, and errors.


## 7. Archived search vocabulary

### Product Management - Inactive

- Product Manager
- Product Owner
- Produktmanager

The first end-to-end run uses this role family only.

### IT Project Management — Archived

Retained as prior scope documentation, but not selected by current runs:

- IT Project Manager
- Digital Project Manager
- Software Project Manager
- Technology Project Manager
- Project Coordinator
- IT Project Coordinator
- Program Coordinator
- Implementation Project Manager
- Customer Project Manager
- Delivery Manager
- Service Delivery Manager
- PMO / PMO Manager
- Projektmanager IT
- IT-Projektmanager
- Digitaler Projektmanager
- Projektkoordinator IT

### Customer Success — Archived

- Customer Success Manager / Specialist / Consultant / Partner / Associate
- Client Success Manager / Partner
- Customer Engagement Manager
- Customer Experience Manager
- Customer Enablement Manager
- Customer Onboarding Manager
- Implementation Manager / Consultant
- Adoption Manager
- Account Manager / Key Account Manager
- Kundenbetreuer / Kundenberater / Customer Success Mitarbeiter

These terms are retained only as an archive of the earlier query inventory and
must not be selected by a prospective collection run.
