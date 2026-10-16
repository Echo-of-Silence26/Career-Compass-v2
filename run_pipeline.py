#!/usr/bin/env python3
"""CLI entry point for the MVP data pipeline.

Example (cost-capped smoke test -- one real Indeed job):
    python run_pipeline.py --sources indeed --max-per-source 1

Provider/model/parameters per stage come from
config/models/model-config-v0.1.yaml (see docs/data_pipeline/MODEL_CONFIG_MVP.md);
this script does not hardcode a model, so which provider actually runs is
whatever that file says. See docs/data_pipeline/DATA_PIPELINE_MVP_SPEC.md for
the full stage design.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv

from pipeline.assessment_schema import SCHEMA_VERSION
from pipeline.candidate_profile import CandidateProfile
from pipeline.model_config import ModelConfigCatalog
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.query_catalog import QueryCatalog
from pipeline.run_manifest import RunManifest
from pipeline.source_adapter import LocationFilter

SOURCE_NAME_ALIASES = {"indeed": "Indeed", "linkedin": "LinkedIn"}
HD_POLICY_VERSION = "hard-disqualifier-v0.2"
FIT_POLICY_VERSION = "capability-fit-v0.3"
EXTRACTION_PROMPT_VERSION = "job-extraction-v0.1"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default="indeed",
                         help="Comma-separated source names: indeed,linkedin")
    parser.add_argument("--max-per-source", type=int, default=0,
                         help="Optional cap on jobs captured per source. "
                              "Use 0 for no quantity cap (default).")
    parser.add_argument("--sourcing-config", default="config/sourcing/sourcing-v0.1.yaml")
    parser.add_argument("--query-set", default="config/sourcing/queries-v0.1.yaml")
    parser.add_argument("--model-config", default="config/models/model-config-v0.1.yaml")
    parser.add_argument("--no-checkpoint", action="store_true",
                         help="Skip the manual checkpoint prompt (non-interactive runs only).")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    load_dotenv()  # populates APIFY_TOKEN / ANTHROPIC_API_KEY from .env into the process environment
    args = parse_args(argv)

    source_names = [SOURCE_NAME_ALIASES.get(s.strip().lower(), s.strip()) for s in args.sources.split(",")]
    max_per_source = None if args.max_per_source == 0 else args.max_per_source

    sourcing_config = yaml.safe_load(Path(args.sourcing_config).read_text(encoding="utf-8"))
    query_catalog = QueryCatalog(Path(args.query_set))
    candidate_profile = CandidateProfile.load()
    model_config_catalog = ModelConfigCatalog(Path(args.model_config))

    manifest = RunManifest.new(
        sourcing_config_version=sourcing_config["sourcing_config_id"],
        candidate_profile_version=candidate_profile.version,
        hard_disqualifier_policy_version=HD_POLICY_VERSION,
        capability_fit_policy_version=FIT_POLICY_VERSION,
        extraction_prompt_version=EXTRACTION_PROMPT_VERSION,
        output_schema_version=SCHEMA_VERSION,
        model_config_version=model_config_catalog.version,
        sources_enabled=source_names,
        max_jobs_per_source=max_per_source,
    )

    run_dir = Path(f"data/runs/{manifest.run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(manifest.to_json(), encoding="utf-8")

    print(f"Run {manifest.run_id} starting.")
    print(f"  sources={source_names} max_per_source={max_per_source}")
    print(f"  model_config_version={model_config_catalog.version}")
    for stage in ("extraction", "hard_disqualifier", "capability_fit"):
        cfg = model_config_catalog.stage_config(stage)
        print(f"    {stage}: {cfg.provider}/{cfg.model}")
    print(f"  candidate_profile_version={candidate_profile.version}")

    candidate_base = sourcing_config["candidate_base"]
    location = LocationFilter(city=candidate_base["city"], country_code=candidate_base["country_code"])

    orchestrator = PipelineOrchestrator(
        manifest=manifest, candidate_profile=candidate_profile, query_catalog=query_catalog,
        location=location, model_config_catalog=model_config_catalog,
        interactive=not args.no_checkpoint,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
