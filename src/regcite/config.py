"""Central settings. Call sites read the model ID from here, never hard-code it."""

from __future__ import annotations

import os

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"


def get_model() -> str:
    return os.environ.get("REGCITE_MODEL", DEFAULT_MODEL)


def get_embedding_model() -> str:
    return os.environ.get("REGCITE_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
