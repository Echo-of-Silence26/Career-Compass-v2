"""Indeed SourceAdapter backed by the Apify actor borderline/indeed-scraper.

Adopted over the (now superseded) Indeed MCP connector per ADR-018. Field mapping follows
docs/data_pipeline/SOURCE_ADAPTER_SPEC_MVP.md §2, verified against the 3
live samples saved at
data/private/fixtures/indeed_apify/apify_probe_raw_2026-08-31.json.

Single call returns full job detail directly — no separate discovery/detail
split (unlike the superseded MCP connector).
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from pipeline.source_adapter import LocationFilter, QueryDefinition, RunContext, SourceAdapter
from pipeline.source_record import SourceRecord, compute_content_hash, utcnow_iso

ACTOR_ID = "borderline/indeed-scraper"
# Tracks the actor's latest published version. Verified live against the
# actor's tagged_builds (2026-09-04): only "latest" exists, not "default".
# SOURCE_ADAPTER_SPEC_MVP.md §2 "Open implementation questions" flags pinning
# an explicit build once the mapping is trusted at volume — left unpinned here.
ACTOR_BUILD = "latest"

ADAPTER_VERSION = "indeed-apify-v0.1"
PARSER_VERSION = "indeed-apify-direct-mapping-v0.1"
CAPTURE_METHOD = "ApifyActor"


class IndeedApifyAdapter(SourceAdapter):
    source = "Indeed"
    source_config_id = "indeed-de-v0.1"
    adapter_version = ADAPTER_VERSION
    parser_version = PARSER_VERSION
    capture_method = CAPTURE_METHOD

    def __init__(self, client=None):
        """client: an apify_client.ApifyClient. Only constructed lazily in
        capture() so importing/using this module for offline mapping (e.g.
        validate_adapters_against_fixtures.py) never requires APIFY_TOKEN."""
        self._client = client

    def _get_client(self):
        if self._client is None:
            from apify_client import ApifyClient
            self._client = ApifyClient(os.environ["APIFY_TOKEN"])
        return self._client

    def capture(self, query: QueryDefinition, location: LocationFilter,
                run_context: RunContext, max_rows: int | None) -> list[SourceRecord]:
        client = self._get_client()
        run_input = {
            "country": location.country_code.lower(),
            "query": query.term,
            "location": location.city,
            "sort": "relevance",
        }
        # Omit optional quantity limits entirely for uncapped collection.
        call_options = {"build": ACTOR_BUILD}
        if max_rows is not None:
            if max_rows <= 0:
                raise ValueError("max_rows must be positive or None")
            run_input["maxRows"] = max_rows
            call_options["max_items"] = max_rows
        run = client.actor(ACTOR_ID).call(run_input=run_input, **call_options)
        items = list(client.dataset(run.default_dataset_id).iterate_items())
        return [self._map_item(item, query, run_context) for item in items]

    def _map_item(self, item: dict[str, Any], query: QueryDefinition,
                  run_context: RunContext) -> SourceRecord:
        """Pure mapping: one raw Apify dataset item -> one SourceRecord.

        Split out from capture() so it can be exercised against saved
        fixtures without any network call.
        """
        raw_title = item.get("title")
        raw_company = item.get("companyName")
        raw_location = item.get("location")
        raw_description = item.get("descriptionText")
        raw_publication_date = item.get("datePublished")
        source_job_id = item.get("jobKey")
        job_url = item.get("jobUrl")

        content_hash = compute_content_hash(
            title=raw_title, company=raw_company, location=raw_location,
            description=raw_description, publication_date=raw_publication_date,
        )

        parser_warnings: list[str] = []
        collection_status = "Success"
        if not raw_description:
            collection_status = "Partial"
            parser_warnings.append("DESCRIPTION_MISSING")
        if not source_job_id:
            parser_warnings.append("SOURCE_ID_MISSING")

        return SourceRecord(
            source_record_id=uuid.uuid4().hex,
            source=self.source,
            source_job_id=source_job_id,
            source_url=job_url,
            resolved_url=job_url,  # already canonical indeed.com/viewjob?jk=..., no redirect resolution needed
            collection_run_id=run_context.run_id,
            sourcing_config_version=run_context.sourcing_config_version,
            source_config_id=self.source_config_id,
            query_group_id=query.query_group_id,
            query_id=query.query_id,
            query_text_or_parameters=query.term,
            captured_at=utcnow_iso(),
            adapter_version=self.adapter_version,
            parser_version=self.parser_version,
            capture_method=self.capture_method,
            raw_title=raw_title,
            raw_company=raw_company,
            raw_location=raw_location,
            raw_description=raw_description,
            raw_publication_date=raw_publication_date,
            # Raw boolean signals, preserved as-is (not yet normalized to a
            # shared Open/Closed or Remote/Hybrid/OnSite/Unknown enum -- see
            # SOURCE_ADAPTER_SPEC_MVP.md §2 open questions).
            raw_job_status=item.get("expired"),
            raw_work_mode=item.get("isRemote"),
            raw_payload_reference="inline",
            content_hash=content_hash,
            collection_status=collection_status,
            parser_warnings=parser_warnings,
            error_code=None,
            raw_payload=item,
        )
