# Sourcing Config

Status: Executable draft v0.1
MVP note (2026-08-20, §5 added 2026-08-30): §3 (active sources), §4
(geography/language), §5 (time window and open status), and §6 (query
groups) are the MVP's config values, used as a single static config file.
§2's versioning lifecycle beyond Draft/Active, §7's cross-source dedup/queue
rules, and §10's SQLite storage decision are parked — see
`DATA_PIPELINE_MVP_SPEC.md` §5.
Created: 2026-08-16
Policy owner: `docs/data_pipeline/SOURCING_POLICY_MVP.md`
Purpose: translate accepted sourcing rules into versioned, executable settings

Machine-readable owner files:

- `config/sourcing/sourcing-v0.1.yaml`;
- `config/sourcing/queries-v0.1.yaml`;
- `config/sourcing/sources/indeed-de-v0.1.yaml`;
- `config/sourcing/sources/linkedin-apify-v0.1.yaml` (renamed from
  `linkedin-extension-v0.1.yaml` when the Apify actor replaced the parked
  Chrome Extension design, ADR-017).

The shared config and atomic query inventory are defined. Source configs remain
Draft until mappings are verified against real, redacted source fixtures; a
null source path must never be interpreted as an implemented mapping.

## 1. Status Legend

- **Confirmed:** agreed and ready to encode.
- **Partial:** direction agreed; implementation detail remains.
- **Open:** requires a decision or source/API investigation.

This document is configuration, not assessment policy. It determines which
searches run and how; it must not use Candidate Profile matching or Capability
Fit to suppress a discovered result.

## 2. Config Identity

| Setting | Current value | Status | Open detail |
|---|---|---|---|
| `sourcing_config_id` | `sourcing-config-v0.1` | Confirmed | None |
| `sourcing_policy_version` | `sourcing-policy-v0.2` | Confirmed | Matches the policy header (Accepted v0.2) |
| `status` | `Draft` | Confirmed | Change to Active only after adapters and queries validate |
| `valid_from` | null | Open | Set at activation |
| `valid_to` | null | Confirmed | Remains null while active |
| `created_at` | `2026-08-16` | Confirmed | None |
| `change_reason` | First executable config framework | Confirmed | None |

## 3. Active Sources

| Source config | Adapter | Enabled | Trigger | Status |
|---|---|---:|---|---|
| `indeed-de-v0.1` | Claude Indeed MCP connector | yes | manual; scheduled post-acceptance | Partial |
| `linkedin-extension-v0.1` | LinkedIn Chrome Extension | no | user-triggered | Parked for MVP |

Credentials are stored only through secret/environment references. No API key,
session cookie, or browser credential may appear in this file or Git.

Source-specific mappings and open implementation questions are owned by
`docs/data_pipeline/SOURCE_ADAPTER_SPEC_MVP.md`.

## 4. Geography, Language, and Work Mode

| Setting | Current value | Status | Open detail |
|---|---|---|---|
| Candidate base | Munich, Germany | Confirmed | Machine-readable coordinates optional |
| Search languages | German, English | Confirmed | Source-specific language parameter support |
| Fully remote | May be globally based; must permit work from Munich/Germany | Confirmed | Detection/mapping per source remains open |
| Hybrid | Munich or approximately 150 km | Confirmed | City/radius implementation and border behavior |
| On-site | Munich or approximately 150 km | Confirmed | City/radius implementation and border behavior |
| Unknown remote eligibility | Collect and mark Unknown | Confirmed | Exact field mapping |

## 5. Time and Incremental Strategy

| Setting | Current value | Status | Open detail |
|---|---|---|---|
| Initial lookback | No business result cap; source-supported open inventory | Confirmed | A technical spend guard is still required |
| Open status | Must still be recruiting for active flow | Confirmed | Source-specific status detection |
| Incremental frequency | Daily at 08:00 Europe/Berlin | Confirmed default | Use source-side newest/date filters before capture where supported |
| Result cap | No business cap | Confirmed | Source/API safety limits still apply and must be logged |
| Incremental cursor | Source-specific | Partial | Indeed supports `fromDays`; current LinkedIn actor supports a date-posted URL/filter. Exact adapter wiring and fallback seen-ID behavior require validation. |
| Incomplete run | Must be recorded as Partial | Confirmed | Completion thresholds per source |

All source publication dates remain raw evidence. For a verified same opening,
the normalized `first_published_at` is the earliest credible date. `first_seen_at`
and `reposted_at` remain separate.

## 6. Query Groups

| Query group ID | Role family | Status | Keywords defined? | Source encoding |
|---|---|---|---:|---|
| `customer-success-v0.1` | Customer Success | Archived | yes | Do not select for prospective runs |
| `growth-v0.1` | Growth | Active | yes | Open |
| `product-management-v0.1` | Product Manager / Product Owner | Active; first-run family | yes | Open |
| `marketing-v0.1` | Marketing | Inactive (2026-08-30) | no | Open |
| `it-project-management-v0.1` | IT Project Management | Inactive | yes | Do not select for current runs |

`marketing-v0.1` has no keyword vocabulary in
`SOURCING_POLICY_MVP.md` §3 and is not activated without a new
Policy version defining one — see `inactive_query_groups` in
`queries-v0.1.yaml`. Marketing is treated as a growth lever (e.g.
`Growth Marketing`, `Product Lead Growth` inside `growth-v0.1`), not a
standalone target role family.

Atomic `QueryDefinition` records are retained in `queries-v0.1.yaml`.
The run-level `active_query_groups` allow only `growth-v0.1` and
`product-management-v0.1`; the first run selects Product Management. CSM and
IT Project Management terms remain as non-runnable historical inventory,
following the two rules below.

### QueryDefinition framework

```yaml
query_id: string
query_group_id: string
source: Indeed | LinkedIn
status: Active | Inactive
keyword_or_expression: string
language: de | en | any
location_expression: string | null
radius_km: number | null
remote_mode: Remote | Hybrid | On-site | Any
source_parameters: object
created_at: datetime
query_version: string
```

Resolved encoding decisions for v0.1:

- use one atomic title per query; adapters may optimize transport only if they
  preserve per-query provenance;
- encode German and English title variants as separate query records;

Remaining open decisions:

- how LinkedIn search-page filters are captured and versioned;
- how overlapping query results are counted without hiding duplicates;
- source-specific filter syntax after fixture/API validation.

Product Marketing remains active under Sourcing Policy v0.1. Changing that
scope requires a new policy/config version.

## 7. Deduplication and Queue Behavior

| Rule | Status |
|---|---|
| Same source ID + same content hash is unchanged | Confirmed |
| Same source ID + changed hash creates a new version | Confirmed |
| Cross-source similarity creates a duplicate candidate, not silent merge | Confirmed |
| Repost does not overwrite original publication date | Confirmed |
| Human workflow states are Unreviewed, Rejected, Applied | Confirmed |
| Only Unreviewed enters the downstream human-review queue | Confirmed |
| Rejected/Applied are not automatically reopened | Confirmed |

Open implementation details:

- canonical URL rules per source;
- exact content-hash input and normalization;
- similarity threshold and human duplicate-review UI;
- how an explicit human reset to Unreviewed is represented.

## 8. Executable Config Skeleton

The eventual machine-readable config should be generated from an approved
version of this framework:

```yaml
sourcing_config_id: sourcing-config-v0.1
sourcing_policy_version: sourcing-policy-v0.2
status: Draft
candidate_base:
  city: Munich
  country: DE
languages: [de, en]
time_window:
  initial_lookback_days: 30
  incremental_frequency: daily
  require_open_for_active_flow: true
sources:
  - source_config_id: indeed-de-v0.1
    enabled: true
  - source_config_id: linkedin-extension-v0.1
    enabled: true
query_groups:
  - id: customer-success-v0.1
    active: false
    lifecycle: archived
  - id: growth-v0.1
    active: true
  - id: product-management-v0.1
    active: true
  - id: marketing-v0.1
    active: false
  - id: it-project-management-v0.1
    active: false
```

## 9. Activation Checklist

- [ ] Resolve every Active-source mapping in `SOURCE_ADAPTER_SPEC_MVP.md`.
- [ ] Encode and test atomic queries for each Active query group.
- [ ] Confirm daily schedule and time zone.
- [ ] Confirm incremental cursor/seen-ID behavior.
- [ ] Validate geography and remote eligibility behavior with fixtures.
- [ ] Validate idempotent retry and duplicate-candidate creation.
- [ ] Confirm `CollectionRun` counters and completion rules.
- [ ] Freeze config version before starting a prospective batch.

## 10. Storage Decision — Parked Design

The earlier storage split was superseded for the first runnable MVP by
ADR-016 and `DATA_PIPELINE_MVP_SPEC.md` §4.4. Current MVP
persistence is JSONL-only. The following remains a post-MVP option:

- immutable raw responses and redacted fixtures: JSON/JSONL;
- structured operational records (`CollectionBatch`, `CollectionRun`,
  `SourceRecord`, and `Job`): SQLite;
- human review and sharing: Excel/CSV exports generated from SQLite.

Excel and CSV are not systems of record and must not be edited and re-imported
as an implicit update path.
