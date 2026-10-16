"""Run-level counters and reconciliation.

Per docs/data_pipeline/DATA_PIPELINE_MVP_SPEC.md §4.8 and MVP Acceptance
Criterion 2: every discovered job must end in exactly one locatable outcome,
and counts must reconcile without silent drops. The physical run_summary.json
layout is this project's own design (Missing P0 -- no spec fixes it).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RunCounts:
    discovered: int = 0
    captured: int = 0

    new: int = 0
    changed: int = 0
    duplicate_unchanged: int = 0

    extraction_failed: int = 0
    blocked: int = 0

    hard_disqualifier_excluded: int = 0
    fit_completed: int = 0
    evaluation_failed: int = 0

    needs_human_review: int = 0


class RunReconciler:
    def __init__(self):
        self.counts = RunCounts()

    def terminal_outcome_total(self) -> int:
        c = self.counts
        return (
            c.duplicate_unchanged
            + c.extraction_failed
            + c.blocked
            + c.hard_disqualifier_excluded
            + c.fit_completed
            + c.evaluation_failed
        )

    def reconcile(self) -> list[str]:
        problems: list[str] = []
        total = self.terminal_outcome_total()
        if total != self.counts.captured:
            problems.append(
                f"captured={self.counts.captured} but terminal outcomes sum to {total} "
                "-- a job may have been silently dropped"
            )
        if self.counts.captured != self.counts.discovered:
            problems.append(
                f"discovered={self.counts.discovered} but captured={self.counts.captured}"
            )
        return problems

    def write_summary(self, run_id: str, path: Path | None = None) -> Path:
        path = path or Path(f"data/runs/{run_id}/run_summary.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "run_id": run_id,
            "counts": asdict(self.counts),
            "reconciliation_problems": self.reconcile(),
        }
        path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
