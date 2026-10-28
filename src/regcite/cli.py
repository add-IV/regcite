"""Command line entry point: ``regcite search "<query>" --corpus data/raw``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from regcite.ingest import ingest, load_corpus
from regcite.search import BM25Index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="regcite")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search the corpus and print citations")
    search.add_argument("query")
    search.add_argument("--corpus", type=Path, default=Path("data/raw"))
    search.add_argument("-k", "--top-k", type=int, default=5)

    fetch = sub.add_parser("ingest", help="Download the regulations and write the manifest")
    fetch.add_argument("--out", type=Path, default=Path("data/raw"))
    fetch.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    fetch.add_argument("--refresh", action="store_true", help="Download again even if cached")

    args = parser.parse_args(argv)

    if args.command == "ingest":
        for entry in ingest(args.out, args.manifest, refresh=args.refresh):
            print(f"{entry['doc_id']}: {entry['version']}, {entry['articles']} articles")
        return 0

    if not args.corpus.is_dir():
        print(f"Corpus folder not found: {args.corpus}", file=sys.stderr)
        return 1

    chunks = load_corpus(args.corpus)
    if not chunks:
        print(f"No .md or .txt files found under {args.corpus}", file=sys.stderr)
        return 1

    results = BM25Index(chunks).search(args.query, top_k=args.top_k)
    if not results:
        print("No matches.")
        return 0

    for rank, (chunk, score) in enumerate(results, start=1):
        print(f"[{rank}] {chunk.doc_id}, line {chunk.line} | {chunk.citation} | score {score:.2f}")
        print(chunk.text)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
