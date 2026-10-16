# Collection Batch and Run Specification

Status: Parked for MVP (2026-08-20) — see `DATA_PIPELINE_MVP_SPEC.md` §5.
The MVP uses a single `run_id` plus an append-only log line per job instead
of this batch/run audit model. Design kept intact for when a multi-run
audit need actually appears.
Created: 2026-08-16
Purpose: define the execution and audit records for prospective sourcing

## 1. Grain and Hierarchy

Use two levels:

```text
CollectionBatch: one logical collection cycle under one config snapshot
  -> CollectionRun: one source adapter x one query/config x one execution
       -> SourceRecord: one immutable source observation
```

A scheduled daily cycle may group many Indeed runs. A LinkedIn manual capture
session may be its own batch or join an open batch; that choice remains open.

## 2. CollectionBatch Schema

| Field | Type | Required | Current status / rule |
|---|---|---:|---|
| `collection_batch_id` | string | yes | Confirmed stable ID |
| `sourcing_policy_version` | string | yes | Confirmed |
| `sourcing_config_version` | string | yes | Confirmed immutable snapshot reference |
| `trigger_type` | enum | yes | Scheduled / Manual |
| `triggered_by` | string/null | no | User/system identity; exact representation open |
| `started_at` | datetime | yes | Confirmed |
| `completed_at` | datetime/null | no | Null while running |
| `status` | enum | yes | Pending / Running / Completed / Partial / Failed / Cancelled |
| `run_ids` | array/relation | yes | One-to-many relationship |
| `summary_counts` | object | yes | Derived from reconciled runs |
| `notes` | text/null | no | Operational annotation, not assessment evidence |

## 3. CollectionRun Schema

| Field | Type | Required | Current status / rule |
|---|---|---:|---|
| `collection_run_id` | string | yes | Confirmed stable execution ID |
| `collection_batch_id` | string | yes | Confirmed parent relation |
| `source` | enum/string | yes | Indeed / LinkedIn initially |
| `source_config_id` | string | yes | Confirmed |
| `query_group_id` | string/null | no | Null only for direct/manual URL capture |
| `query_id` | string/null | no | Atomic query identity |
| `sourcing_policy_version` | string | yes | Confirmed |
| `sourcing_config_version` | string | yes | Confirmed |
| `adapter_version` | string | yes | Confirmed |
| `parser_version` | string | yes | Confirmed |
| `trigger_type` | enum | yes | Scheduled / Manual / Retry |
| `triggered_by` | string/null | no | Representation open |
| `started_at` | datetime | yes | Confirmed |
| `completed_at` | datetime/null | no | Confirmed |
| `status` | enum | yes | Pending / Running / Completed / Partial / Failed / Cancelled |
| `cursor_in` | object/null | no | Source-specific; open mapping |
| `cursor_out` | object/null | no | Source-specific; open mapping |
| `retry_of_run_id` | string/null | no | Links retry without overwriting failed run |
| `completion_reason` | string/null | no | Required for Partial/Failed/Cancelled |
| `error_summary` | object/null | no | Structured counts and representative codes |

## 4. Required Counters

```text
reported_result_count
results_scanned
records_discovered
records_captured
records_created
records_unchanged
records_updated
repost_candidates
duplicate_candidates
closed_records
partial_records
failed_records
results_left_unscanned
```

Definitions still need executable invariants. Initial recommendations:

- `results_scanned` counts source result items inspected, not detail pages;
- `records_captured` counts emitted SourceRecords, including Partial records;
- created/unchanged/updated classify successfully identified records and must
  not double-count one observation;
- failures do not disappear from totals;
- `results_left_unscanned` may be Unknown when the source exposes no reliable
  total;
- a run cannot be `Completed` when a known positive number remains unscanned.

## 5. Status Rules

### `Completed`

The intended query/config scope completed, counters reconcile, and no known
results were left unscanned. Individual record warnings may still exist.

### `Partial`

Useful records were captured, but the intended scope was not completed—for
example rate limiting, manual early stop, unprocessed pages, or an extension
submission failure affecting only part of the session.

### `Failed`

The run produced no trustworthy completion of its intended scope. Any emitted
raw records remain immutable and are not erased.

### `Cancelled`

An explicit user/system cancellation. The reason and partial outputs remain.

## 6. Retry and Idempotency

- A retry creates a new `collection_run_id` and sets `retry_of_run_id`.
- Reprocessing the same source observation must not create uncontrolled Job or
  SourceRecord duplicates.
- Failed and partial runs remain in the audit history.
- Cursor advancement occurs only according to a source-specific safe-commit
  rule; those rules remain open in `SOURCE_ADAPTER_SPEC_MVP.md`.

## 7. Reconciliation Checks

Before a run becomes Completed:

- [ ] every emitted SourceRecord references this run;
- [ ] counters match persisted records and identity outcomes;
- [ ] known source totals reconcile with scanned and left-unscanned counts;
- [ ] every failure has an error code;
- [ ] Partial/Failed/Cancelled has a completion reason;
- [ ] policy/config/adapter/parser versions are present;
- [ ] no secret or browser-session data appears in run metadata.

## 8. Open Decisions

- Whether LinkedIn manual sessions form separate batches or join a daily batch.
- Exact batch boundary and daily schedule/time zone.
- Counter invariants when one search result emits discovery and detail records.
- Source-specific safe cursor-commit behavior.
- Retention period for verbose error details and raw payload references.
- Whether direct/manual URL capture requires a synthetic query ID.
- Whether a partially captured job can be completed by a later run while
  retaining both SourceRecords.

