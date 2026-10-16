# MVP Architecture

Status: Active MVP summary — runtime details are owned by
`docs/data_pipeline/DATA_PIPELINE_MVP_SPEC.md` v0.9.

```text
Indeed + LinkedIn discovery and raw capture
  -> persist raw evidence
  -> exact pre-extraction deduplication
  -> LLM flat-Job extraction
  -> minimal input guard
  -> Hard Disqualifier LLM
  -> Capability Fit LLM when no confirmed Fail
  -> append-only JSONL result
  -> Excel human-review export
```

## System Boundary

The first runnable MVP manually starts one Product Management run across the
Indeed and LinkedIn Apify adapters. Growth is the second active role family;
Customer Success is archived for prospective sourcing while its historical
evaluation baseline is retained. Scheduled daily execution is enabled only
after manual acceptance. The system does not submit applications.

## Module Responsibilities

| Module | Responsibility | Deterministic / Probabilistic |
|---|---|---|
| Indeed + LinkedIn adapters | Discover and capture raw JD evidence | Deterministic code + Apify API |
| Deduplicator | Skip unchanged `source + source_job_id` records before LLM extraction | Deterministic |
| Job extractor | Convert connector markdown to the flat Job JSON | LLM |
| Minimal input guard | Check JSON parseability and required non-empty inputs | Deterministic |
| Hard Disqualifier / Fit | Execute the two frozen policies as separate calls | LLM |
| Human application decision | Present every non-failed job and its Fit evidence for human review; Fit does not cause or prevent application | Human-owned |
| Evaluation harness | Run fixed datasets, calculate metrics, compare versions | Deterministic orchestration |
| Human review | Resolve Hard-Disqualifier boundaries, review Fit, and make the final application decision | Human |

## Initial Technology Choices

- Python 3.12
- Minimal JSON parsing and required-input checks for the first run
- Pytest for rules, transformations, and regression tests
- Typer for a minimal CLI
- Append-only JSONL; SQLite is post-MVP unless observed needs justify it
- One LLM provider to limit integration variables

## Engineering-Depth Boundary

Required: APIs, schemas, data flow, logging, error handling, caching, versioning, and tests.
Out of scope: microservices, distributed systems, complex cloud deployment, vector databases, and multi-agent orchestration.

## Open Architecture Questions

- Do historical records contain enough complete job descriptions to rerun assessments?
- Should candidate evidence use structured JSON or Markdown plus a parser?
- How should responsibility for language constraints be divided between rules and the LLM?
