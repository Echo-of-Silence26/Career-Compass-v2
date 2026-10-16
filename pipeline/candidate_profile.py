"""Loader for the fixed, versioned Candidate Profile artifact.

Resolves the "Candidate Profile artifact/version contract" gap that blocks
Hard Disqualifier and Capability Fit (build-tracker cross-cutting item 5).
The content itself
(config/candidate_profile/candidate-profile-v0.1.yaml) is a Claude-drafted
first pass from the candidate's CV -- flagged DRAFT there until reviewed.

`content_hash` is computed from the file bytes at load time rather than
stored inside the YAML, to avoid a hash-of-itself problem.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_PATH = Path("config/candidate_profile/candidate-profile-v0.1.yaml")


@dataclass
class CandidateProfile:
    data: dict
    version: str
    content_hash: str
    path: Path

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "CandidateProfile":
        raw = path.read_bytes()
        content_hash = hashlib.sha256(raw).hexdigest()
        data = yaml.safe_load(raw.decode("utf-8"))
        version = data.get("profile_version")
        if not version:
            raise ValueError(f"Candidate Profile at {path} is missing 'profile_version'")
        return cls(data=data, version=version, content_hash=content_hash, path=path)

    def as_prompt_text(self) -> str:
        """Stable text rendering to embed directly in HD/Fit prompts."""
        return yaml.safe_dump(self.data, sort_keys=False, allow_unicode=True)
