"""Tests for the offline search-quality benchmark evaluator."""

from __future__ import annotations

import pytest

from thesisagents.evaluation.search_quality import evaluate_benchmark, evaluate_query


def test_evaluate_query_reports_precision_recall_and_ndcg():
    metrics = evaluate_query(
        ["cornerstone", "noise", "related"],
        {"cornerstone": 2, "related": 1, "missed": 1},
        cutoff=3,
    )
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert 0 < metrics["ndcg"] < 1


def test_evaluate_benchmark_accepts_binary_and_graded_qrels():
    report = evaluate_benchmark(
        {
            "queries": [
                {"id": "q1", "retrieved": ["a", "x"], "relevance": ["a"]},
                {"id": "q2", "retrieved": ["b", "c"], "relevance": {"b": 2}},
            ]
        },
        cutoff=2,
    )
    assert report["query_count"] == 2
    assert report["macro"]["precision"] == pytest.approx(0.5)
    assert report["macro"]["recall"] == pytest.approx(1.0)


def test_evaluate_benchmark_rejects_missing_queries():
    with pytest.raises(ValueError, match="queries"):
        evaluate_benchmark({})


def test_evaluate_query_rejects_zero_cutoff():
    with pytest.raises(ValueError, match="cutoff"):
        evaluate_query([], {}, cutoff=0)
