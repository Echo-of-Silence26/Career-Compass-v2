"""Offline check: run each adapter's field-mapping logic against the saved
Apify probe fixtures and print the resulting SourceRecords.

Deliberately makes zero network/Apify calls -- constructs each adapter with
client=None and calls only its private _map_item() mapping function, not
capture(). Confirms the mapping code in pipeline/adapters/*.py matches the
same raw JSON shape documented in
docs/data_pipeline/SOURCE_ADAPTER_SPEC_MVP.md §2/§4, without spending any
Apify credit.

Run: python -m pipeline.validate_adapters_against_fixtures
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pipeline.adapters.indeed_apify import IndeedApifyAdapter
from pipeline.adapters.linkedin_apify import LinkedInApifyAdapter
from pipeline.source_adapter import QueryDefinition, RunContext

INDEED_FIXTURE = Path("data/private/fixtures/indeed_apify/apify_probe_raw_2026-08-31.json")
LINKEDIN_FIXTURE = Path("data/private/fixtures/linkedin/apify_probe_raw_2026-08-31.json")

REQUIRED_NON_NULL = [
    "source_record_id", "source", "collection_run_id", "sourcing_config_version",
    "source_config_id", "query_group_id", "query_id", "captured_at",
    "adapter_version", "parser_version", "capture_method", "raw_title",
    "content_hash", "collection_status",
]


def _check(record) -> list[str]:
    problems = []
    d = asdict(record)
    for field_name in REQUIRED_NON_NULL:
        if d.get(field_name) in (None, ""):
            problems.append(f"missing required field: {field_name}")
    return problems


def run() -> None:
    run_context = RunContext.new(sourcing_config_version="sourcing-config-v0.1")
    query = QueryDefinition(
        query_id="cs-customer-success-manager-en-v0.1",
        query_group_id="customer-success-v0.1",
        term="Customer Success Manager",
        language="en",
    )

    total_problems = 0

    print("=== Indeed ===")
    indeed_items = json.loads(INDEED_FIXTURE.read_text())
    indeed_adapter = IndeedApifyAdapter(client=None)
    for raw_item in indeed_items:
        record = indeed_adapter._map_item(raw_item, query, run_context)
        problems = _check(record)
        total_problems += len(problems)
        status = "OK" if not problems else "PROBLEMS: " + "; ".join(problems)
        print(f"- {record.source_job_id} | {record.raw_title!r} | "
              f"status={record.collection_status} warnings={record.parser_warnings} | {status}")

    print("\n=== LinkedIn ===")
    linkedin_items = json.loads(LINKEDIN_FIXTURE.read_text())
    linkedin_adapter = LinkedInApifyAdapter(client=None)
    for raw_item in linkedin_items:
        record = linkedin_adapter._map_item(raw_item, query, run_context)
        problems = _check(record)
        total_problems += len(problems)
        status = "OK" if not problems else "PROBLEMS: " + "; ".join(problems)
        print(f"- {record.source_job_id} | {record.raw_title!r} | resolved_url={record.resolved_url} | "
              f"status={record.collection_status} warnings={record.parser_warnings} | {status}")

    print(f"\n{len(indeed_items)} Indeed + {len(linkedin_items)} LinkedIn fixture items mapped, "
          f"{total_problems} problems found.")
    if total_problems:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
