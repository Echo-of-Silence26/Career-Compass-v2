"""LinkedIn SourceAdapter backed by the Apify actor curious_coder/linkedin-jobs-scraper.

Un-parked from the Chrome Extension design per ADR-017. Field mapping follows
docs/data_pipeline/SOURCE_ADAPTER_SPEC_MVP.md §4, verified against the 2
live samples saved at
data/private/fixtures/linkedin/apify_probe_raw_2026-08-31.json.

Single call returns full job detail directly, same discovery+detail
collapse as the Indeed Apify adapter.
"""

from __future__ import annotations

import os
import uuid
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from pipeline.source_adapter import LocationFilter, QueryDefinition, RunContext, SourceAdapter
from pipeline.source_record import SourceRecord, compute_content_hash, utcnow_iso

ACTOR_ID = "curious_coder/linkedin-jobs-scraper"
# Probe used the "latest" build (unpinned) -- same open question and same
# deliberately-not-called-live-this-pass reasoning as the Indeed adapter.
ACTOR_BUILD = "latest"

ADAPTER_VERSION = "linkedin-apify-v0.1"
PARSER_VERSION = "linkedin-apify-direct-mapping-v0.1"
CAPTURE_METHOD = "ApifyActor"


def _search_url(term: str, city: str, country_code: str) -> str:
    location = f"{city}, {country_code}"
    return (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={quote(term)}&location={quote(location)}"
    )


def _strip_tracking_params(link: str) -> str:
    """link -> resolved_url: drop query/fragment (position, pageNum, refId,
    trackingId are search-session tracking, not part of job identity), per
    SOURCE_ADAPTER_SPEC_MVP.md §4 resolved_url row."""
    parts = urlsplit(link)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


class LinkedInApifyAdapter(SourceAdapter):
    source = "LinkedIn"
    source_config_id = "linkedin-apify-v0.1"
    adapter_version = ADAPTER_VERSION
    parser_version = PARSER_VERSION
    capture_method = CAPTURE_METHOD

    def __init__(self, client=None):
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
            "urls": [_search_url(query.term, location.city, location.country_code)],
            "scrapeCompany": True,
        }
        # Omit optional quantity limits entirely for uncapped collection.
        call_options = {"build": ACTOR_BUILD}
        if max_rows is not None:
            if max_rows <= 0:
                raise ValueError("max_rows must be positive or None")
            run_input["limitPerSource"] = max_rows
            call_options["max_items"] = max_rows
        run = client.actor(ACTOR_ID).call(run_input=run_input, **call_options)
        items = list(client.dataset(run.default_dataset_id).iterate_items())
        return [self._map_item(item, query, run_context) for item in items]

    def _map_item(self, item: dict[str, Any], query: QueryDefinition,
                  run_context: RunContext) -> SourceRecord:
        raw_title = item.get("title")
        raw_company = item.get("companyName")
        raw_location = item.get("location")
        raw_description = item.get("descriptionText")
        raw_publication_date = item.get("postedAt")
        source_job_id = item.get("id")
        link = item.get("link")
        resolved_url = _strip_tracking_params(link) if link else None

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
            source_url=link,
            resolved_url=resolved_url,
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
            # Not available from this actor at all (SOURCE_ADAPTER_SPEC_MVP.md
            # §4) -- left null rather than inferred.
            raw_job_status=None,
            raw_work_mode=None,
            raw_payload_reference="inline",
            content_hash=content_hash,
            collection_status=collection_status,
            parser_warnings=parser_warnings,
            error_code=None,
            raw_payload=item,
        )
