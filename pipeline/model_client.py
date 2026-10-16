"""Provider-agnostic model-calling interface.

Per docs/data_pipeline/MODEL_CONFIG_MVP.md: Policy defines decision rules,
Prompt defines task instructions, Model Config pins provider/model/params.
JobExtractor/HardDisqualifierEvaluator/CapabilityFitEvaluator depend only on
`ModelClient` -- never on `anthropic` directly -- so swapping providers means
adding one new class here and a config line in
config/models/model-config-v0.1.yaml, not touching any of the three callers.

Only `AnthropicModelClient` exists today (the only SDK this project has
integrated and offline-validated against); adding another provider is a
follow-on task, not a redesign.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ModelCallUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class ModelCallResult:
    text: str
    usage: ModelCallUsage


class ModelClient(ABC):
    """One provider-neutral call: optional cached system context + one user
    turn -> response text + usage. Callers never see provider-specific
    request/response shapes."""

    @abstractmethod
    def complete(self, *, system_blocks: list[str], user_message: str,
                 max_tokens: int, temperature: float = 0,
                 output_schema: dict[str, Any] | None = None) -> ModelCallResult:
        """`output_schema`, when given, is a JSON Schema object requesting a
        provider's native structured-output mode -- the response is
        guaranteed to be exactly that schema's shape (no markdown fencing,
        no commentary), rather than merely asked for via prompt instructions."""
        raise NotImplementedError


class AnthropicModelClient(ModelClient):
    """Wraps the Anthropic Python SDK. The last system block is marked
    cache_control: ephemeral when system_blocks is non-empty -- the caller
    decides whether to pass a stable system context at all (per stage's
    use_prompt_caching in the Model Config)."""

    def __init__(self, model: str, client=None):
        self.model = model
        self._client = client

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def complete(self, *, system_blocks: list[str], user_message: str,
                 max_tokens: int, temperature: float = 0,
                 output_schema: dict[str, Any] | None = None) -> ModelCallResult:
        client = self._get_client()
        system = [{"type": "text", "text": block} for block in system_blocks]
        if system:
            system[-1] = {**system[-1], "cache_control": {"type": "ephemeral"}}

        import anthropic

        create_kwargs = dict(
            model=self.model, max_tokens=max_tokens,
            system=system, messages=[{"role": "user", "content": user_message}],
        )
        if output_schema is not None:
            create_kwargs["output_config"] = {
                "format": {"type": "json_schema", "schema": output_schema}
            }
        try:
            response = client.messages.create(extra_body={"temperature": temperature}, **create_kwargs)
        except anthropic.BadRequestError as e:
            # Some models (e.g. claude-sonnet-5) reject `temperature` outright --
            # "`temperature` is deprecated for this model" -- rather than only
            # rejecting non-default values. Retry once without it.
            if "temperature" not in str(e):
                raise
            response = client.messages.create(**create_kwargs)
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        usage = getattr(response, "usage", None)
        return ModelCallResult(
            text=text,
            usage=ModelCallUsage(
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            ),
        )
