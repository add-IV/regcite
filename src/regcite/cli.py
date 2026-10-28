"""Command line entry point: ``regcite search "<query>" --corpus data/raw``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from regcite.evaluate import evaluate_retrieval, summarise
from regcite.gold import load_gold
from regcite.ingest import ingest, load_corpus
from regcite.rankers import RANKERS, build_ranker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="regcite")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search the corpus and print citations")
    search.add_argument("query")
    search.add_argument("--corpus", type=Path, default=Path("data/raw"))
    search.add_argument("-k", "--top-k", type=int, default=5)
    search.add_argument("--ranker", choices=RANKERS, default="bm25")
    search.add_argument("--index", type=Path, default=Path("data/index"), help="Vector cache")

    fetch = sub.add_parser("ingest", help="Download the regulations and write the manifest")
    fetch.add_argument("--out", type=Path, default=Path("data/raw"))
    fetch.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    fetch.add_argument("--refresh", action="store_true", help="Download again even if cached")

    evaluate = sub.add_parser("eval", help="Compare rankers on the gold questions")
    evaluate.add_argument("--corpus", type=Path, default=Path("data/raw"))
    evaluate.add_argument("--gold", type=Path, default=Path("eval/gold.jsonl"))
    evaluate.add_argument("--rankers", nargs="+", choices=RANKERS, default=list(RANKERS))
    evaluate.add_argument("-k", "--top-k", type=int, default=5)
    evaluate.add_argument("--index", type=Path, default=Path("data/index"), help="Vector cache")

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

    if args.command == "eval":
        return _run_eval(args, chunks)

    results = build_ranker(args.ranker, chunks, args.index).search(args.query, top_k=args.top_k)
    if not results:
        print("No matches.")
        return 0

    for rank, (chunk, score) in enumerate(results, start=1):
        print(f"[{rank}] {chunk.doc_id}, line {chunk.line} | {chunk.citation} | score {score:.2f}")
        print(chunk.text)
        print()
    return 0


def _run_eval(args, chunks) -> int:
    questions = load_gold(args.gold)
    print(f"{'ranker':<8} {'group':<17} {'n':>3} {f'recall@{args.top_k}':>9} {'MRR':>6}")
    for name in args.rankers:
        ranker = build_ranker(name, chunks, args.index)
        results = evaluate_retrieval(ranker, questions, k=args.top_k)
        for group, stats in summarise(results).items():
            recall, mrr = stats["recall"], stats["mrr"]
            print(f"{name:<8} {group:<17} {stats['n']:>3} {recall:>9.2f} {mrr:>6.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
