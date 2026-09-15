"""Standard ranking metrics for deterministic retrieval evaluation."""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from agent_search.corpus.schemas import ChunkRelevanceJudgment, SearchResult


@dataclass(frozen=True)
class MetricSummary:
    """Mean ranking metrics at a fixed result cutoff."""

    recall: float
    mrr: float
    ndcg: float


def evaluate(
    results_by_query: dict[str, Sequence[SearchResult]],
    judgments: Iterable[ChunkRelevanceJudgment],
    *,
    k: int,
) -> MetricSummary:
    """Calculate mean Recall@k, MRR@k, and nDCG@k across judged queries."""

    if k < 1:
        raise ValueError("k must be positive")
    qrels: dict[str, dict[str, int]] = {}
    for judgment in judgments:
        qrels.setdefault(judgment.query_id, {})[judgment.chunk_id] = judgment.relevance
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    for query_id, relevant in qrels.items():
        retrieved = list(results_by_query.get(query_id, []))[:k]
        gains = [relevant.get(result.chunk_id, 0) for result in retrieved]
        recalls.append(sum(gain > 0 for gain in gains) / len(relevant))
        first = next((rank for rank, gain in enumerate(gains, start=1) if gain > 0), None)
        reciprocal_ranks.append(1 / first if first else 0)
        actual = sum((2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(gains, 1))
        ideal_gains = sorted(relevant.values(), reverse=True)[:k]
        ideal = sum(
            (2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(ideal_gains, 1)
        )
        ndcgs.append(actual / ideal if ideal else 0)
    return MetricSummary(
        recall=sum(recalls) / len(recalls),
        mrr=sum(reciprocal_ranks) / len(reciprocal_ranks),
        ndcg=sum(ndcgs) / len(ndcgs),
    )
