"""Read-only lookup over config/sourcing/queries-v0.1.yaml.

Used by JobExtractor's deterministic passthrough (JOB_EXTRACTION_PROMPT_MVP.md
§2: `matched_search_terms`/`role_family` are "copied/derived from the
RawJobRecord's query_id -> query_group_id -> role_family lookup ... never
re-derived from JD text").
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_PATH = Path("config/sourcing/queries-v0.1.yaml")


@dataclass
class QueryDef:
    query_id: str
    query_group_id: str
    role_family: str
    term: str
    language: str
    status: str


class QueryCatalog:
    def __init__(self, path: Path = DEFAULT_PATH):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self._order: list[str] = []
        self._by_id: dict[str, QueryDef] = {}
        for row in data["queries"]:
            self._by_id[row["query_id"]] = QueryDef(
                query_id=row["query_id"],
                query_group_id=row["query_group_id"],
                role_family=row["role_family"],
                term=row["term"],
                language=row["language"],
                status=row.get("status", "Active"),
            )
            self._order.append(row["query_id"])
        # Per the file's own header comment: "Run-level scope is authoritative
        # over the legacy per-query `status` field." Every individual query row
        # still carries status: Active (never cleaned up when groups were
        # archived), so active_query_groups is the only thing that actually
        # reflects which groups are in scope -- verified live 2026-09-05 when
        # an archived customer-success-v0.1 query still surfaced in a run.
        self._active_query_groups = set(data.get("active_query_groups", []))

    def get(self, query_id: str) -> QueryDef:
        try:
            return self._by_id[query_id]
        except KeyError:
            raise ValueError(f"Unknown query_id {query_id!r} -- not in {DEFAULT_PATH}") from None

    def all(self) -> list[QueryDef]:
        return [self._by_id[qid] for qid in self._order]

    def active(self) -> list[QueryDef]:
        return [q for q in self.all()
                if q.status == "Active" and q.query_group_id in self._active_query_groups]
