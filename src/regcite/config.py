"""Central settings. Call sites read the model ID from here, never hard-code it."""

from __future__ import annotations

import os

DEFAULT_MODEL = "claude-sonnet-5-5"


def get_model() -> str:
    return os.environ.get("REGCITE_MODEL", DEFAULT_MODEL)
