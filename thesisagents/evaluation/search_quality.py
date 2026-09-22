"""Deterministic ranking metrics for a manually judged search benchmark.

The evaluator is deliberately network-free so the same result can run in CI.
Each query supplies ranked retrieved IDs plus relevance judgements, then this
module reports precision, recall and nDCG at a selected cutoff.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def evaluate_query(
    retrieved: Sequence[str],
    relevance: Mapping[str, int],
    *,
    cutoff: int = 10,
) -> dict[str, float | int]:
    """Evaluate one ranked result list against graded relevance judgements.

    Grades greater than zero count as relevant for precision and recall. nDCG
    retains the grade, so putting a grade-2 cornerstone paper before a grade-1
    related paper receives more credit.

    Example: ``evaluate_query(["a", "x"], {"a": 2}, cutoff=2)`` returns
    perfect recall and precision 0.5.
    """
    if cutoff < 1:
        raise ValueError("cutoff must be at least 1")
    ranked = list(retrieved[:cutoff])
    relevant = {paper_id for paper_id, grade in relevance.items() if grade > 0}
    hits = sum(paper_id in relevant for paper_id in ranked)
    precision = hits / cutoff
    recall = hits / len(relevant) if relevant else 0.0
    dcg = _dcg([relevance.get(paper_id, 0) for paper_id in ranked])
    ideal = sorted((grade for grade in relevance.values() if grade > 0), reverse=True)
    idcg = _dcg(ideal[:cutoff])
    return {
        "cutoff": cutoff,
        "retrieved": len(ranked),
        "relevant": len(relevant),
        "hits": hits,
        "precision": precision,
        "recall": recall,
        "ndcg": dcg / idcg if idcg else 0.0,
    }


def evaluate_benchmark(payload: Mapping[str, Any], *, cutoff: int = 10) -> dict[str, Any]:
    """Evaluate every query in a benchmark payload and return macro averages.

    Payloads use ``{"queries": [{"id", "retrieved", "relevance"}]}``.
    Relevance may be a mapping of paper ID to integer grade or a list of
    relevant IDs, which is treated as binary grade 1.
    """
    queries = payload.get("queries")
    if not isinstance(queries, list) or not queries:
        raise ValueError("benchmark must contain a non-empty queries list")
    rows: list[dict[str, Any]] = []
    for item in queries:
        query_id = str(item.get("id") or "").strip()
        if not query_id:
            raise ValueError("every benchmark query requires an id")
        retrieved = item.get("retrieved") or []
        relevance = _coerce_relevance(item.get("relevance"))
        metrics = evaluate_query(retrieved, relevance, cutoff=cutoff)
        rows.append({"id": query_id, **metrics})
    macro = {
        key: sum(float(row[key]) for row in rows) / len(rows)
        for key in ("precision", "recall", "ndcg")
    }
    return {"cutoff": cutoff, "query_count": len(rows), "macro": macro, "queries": rows}


def _coerce_relevance(value: object) -> dict[str, int]:
    """Normalise binary-list and graded-map qrels into integer grades."""
    if isinstance(value, list):
        return {str(paper_id): 1 for paper_id in value}
    if isinstance(value, dict):
        result = {str(paper_id): int(grade) for paper_id, grade in value.items()}
        if any(grade < 0 for grade in result.values()):
            raise ValueError("relevance grades cannot be negative")
        return result
    raise ValueError("relevance must be a list of IDs or an ID-to-grade mapping")


def _dcg(grades: Sequence[int]) -> float:
    """Compute discounted cumulative gain using exponential graded gain."""
    return sum((2**grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(grades))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the offline evaluator against a JSON benchmark file."""
    parser = argparse.ArgumentParser(description="Evaluate ranked paper-search results.")
    parser.add_argument("benchmark", type=Path, help="JSON benchmark path")
    parser.add_argument("--cutoff", "-k", type=int, default=10)
    args = parser.parse_args(argv)
    payload = json.loads(args.benchmark.read_text(encoding="utf-8"))
    print(json.dumps(evaluate_benchmark(payload, cutoff=args.cutoff), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
