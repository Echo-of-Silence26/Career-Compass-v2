"""Loader for config/models/model-config-v0.1.yaml.

Resolves provider/model/parameters per stage into a pluggable ModelClient
(pipeline/model_client.py), so job_extractor.py/hard_disqualifier.py/
capability_fit.py never import a provider SDK directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from pipeline.model_client import AnthropicModelClient, ModelClient

DEFAULT_PATH = Path("config/models/model-config-v0.1.yaml")

PROVIDER_CLIENTS: dict[str, type[ModelClient]] = {
    "anthropic": AnthropicModelClient,
}


@dataclass
class StageModelConfig:
    provider: str
    model: str
    temperature: float
    max_tokens: int
    use_prompt_caching: bool
    max_attempts: int


class ModelConfigCatalog:
    def __init__(self, path: Path = DEFAULT_PATH):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.version = data["model_config_version"]
        self._stages: dict[str, StageModelConfig] = {}
        for name, cfg in data["stages"].items():
            self._stages[name] = StageModelConfig(
                provider=cfg["provider"],
                model=cfg["model"],
                temperature=cfg.get("temperature", 0),
                max_tokens=cfg["max_tokens"],
                use_prompt_caching=cfg.get("use_prompt_caching", False),
                max_attempts=cfg.get("retry", {}).get("max_attempts", 1),
            )

    def stage_config(self, stage: str) -> StageModelConfig:
        try:
            return self._stages[stage]
        except KeyError:
            raise ValueError(f"Unknown stage {stage!r} -- not in {DEFAULT_PATH}") from None

    def build_client(self, stage: str, client_override=None) -> ModelClient:
        cfg = self.stage_config(stage)
        cls = PROVIDER_CLIENTS.get(cfg.provider)
        if cls is None:
            raise ValueError(
                f"Unknown provider {cfg.provider!r} for stage {stage!r} -- "
                f"add an implementation to pipeline/model_client.py and register it "
                f"in PROVIDER_CLIENTS"
            )
        return cls(model=cfg.model, client=client_override)
