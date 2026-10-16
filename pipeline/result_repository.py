"""Append-only JSONL persistence for canonical Jobs and evaluation results.

Physical layout is this project's own design (flagged Missing P0 in
DATA_PIPELINE_MVP_SPEC.md §9 -- no spec fixes file layout), chosen to keep
ADR-016's "JSONL-only, append-only" rule while satisfying
JOB_SCHEMA_MVP.md's "update the current Job record, no historical
versions" rule: a `changed` outcome appends a new line rather than rewriting
the file in place, and the *last* line for a given job_id is authoritative on
read. Evaluation results are never updated in place -- each run's result is a
new, permanently retained line (EVAL_RESULT_SCHEMA_MVP.md §6).
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.assessment_schema import EvaluationResult
from pipeline.job_schema import Job

DEFAULT_JOBS_PATH = Path("data/jobs/jobs.jsonl")
DEFAULT_EVALUATIONS_PATH = Path("data/evaluations/evaluations.jsonl")


class JobRepository:
    def __init__(self, path: Path = DEFAULT_JOBS_PATH):
        self.path = path

    def append(self, job: Job) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(job.to_json_line() + "\n")

    def read_current(self) -> dict[str, Job]:
        """Last line per job_id wins -- see module docstring."""
        current: dict[str, Job] = {}
        if not self.path.exists():
            return current
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                current[d["job_id"]] = Job.from_dict(d)
        return current


class EvaluationRepository:
    def __init__(self, path: Path = DEFAULT_EVALUATIONS_PATH):
        self.path = path

    def append(self, result: EvaluationResult) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(result.model_dump_json() + "\n")

    def read_all_for_run(self, run_id: str) -> list[EvaluationResult]:
        results: list[EvaluationResult] = []
        if not self.path.exists():
            return results
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("run_id") == run_id:
                    results.append(EvaluationResult(**d))
        return results
