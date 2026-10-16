# Model Configuration — MVP

Status: Draft v0.1

`config/models/model-config-v0.1.yaml` is the machine-readable Model Config.
It answers which provider/model and execution parameters run each LLM stage.
It does not define assessment meaning:

- Policy defines the decision rules and allowed labels.
- Prompt defines the task instructions and request/response envelope.
- Model Config pins the provider, model identifier, temperature, structured
  output mode, retry behavior, and usage/cost logging.
- Evaluator loads all three and validates the returned result schema.

The extraction, Hard Disqualifier, and Capability Fit stages may use the same
model initially to reduce integration variables. Exact model identifiers remain
TBD until integration, then must be frozen before the first comparable run.
