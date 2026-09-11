# Synthetic data

This directory contains deterministic, fictional news and financial-document
fixtures. No real documents, user interaction logs, personally identifiable
information, or proprietary material belongs here.

## Files

- `documents.jsonl`: ten synthetic documents across `news` and `finance`.
- `queries.jsonl`: six English and Korean evaluation queries.
- `qrels.jsonl`: eleven graded query-document relevance judgments, from 1 to 3.

Every record declares schema version `1.0`. Regenerate the committed fixtures
from the repository root with:

```bash
python -m agent_search.corpus.generator
```

The generator contains fixed source content and a stable key order, making the
fixtures reproducible and their diffs reviewable.
