"""Loading regulation texts into citable chunks."""

from regcite.ingest.corpus import SUPPORTED_SUFFIXES, load_corpus
from regcite.ingest.pipeline import ingest

__all__ = ["SUPPORTED_SUFFIXES", "ingest", "load_corpus"]
