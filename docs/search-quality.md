# Search-quality benchmark

Unit tests prove that parsers and ranking rules behave as designed. This
offline benchmark answers a different question: whether ranked results are
actually relevant to representative research queries.

Create a UTF-8 JSON file with stable paper identifiers. DOI is preferred,
followed by arXiv ID. Grade 2 means a cornerstone paper, grade 1 means relevant,
and omitted IDs are treated as non-relevant.

```json
{
  "queries": [
    {
      "id": "llm-code-review",
      "retrieved": ["10.1000/example", "arxiv:2501.00001"],
      "relevance": {
        "10.1000/example": 2,
        "arxiv:2501.00001": 1
      }
    }
  ]
}
```

Run the evaluator without network access:

```powershell
py -m thesisagents.evaluation.search_quality benchmark.json --cutoff 10
```

The benchmark path is read relative to `--root`, which defaults to the current
directory; absolute paths and `..` segments are refused, like every other
user-supplied path in this project. A benchmark kept elsewhere is reached by
naming its directory:

```powershell
py -m thesisagents.evaluation.search_quality bench.json --root D:\data\qrels
```

The report includes per-query and macro Precision@K, Recall@K and nDCG@K.
Judgements should be reviewed by a domain reader, committed separately from
retrieved results, and updated only when the relevance standard changes.
