"""Run lexical, vector, and RRF benchmarks over the synthetic chunk corpus."""

from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter

from agent_search.corpus.embeddings import EmbeddingProvider, embed_chunks
from agent_search.corpus.schemas import (
    ChunkRecord,
    ChunkRelevanceJudgment,
    SearchQuery,
    SearchResult,
)
from agent_search.evaluation.metrics import MetricSummary, evaluate
from agent_search.retrieval.lexical import LocalBM25Retriever
from agent_search.retrieval.semantic import EmbeddingSpec, HybridRetriever, LocalVectorRetriever


@dataclass(frozen=True)
class BenchmarkResult:
    """Metrics and mean per-query latency for one retrieval configuration."""

    name: str
    metrics: MetricSummary
    mean_latency_ms: float


def benchmark(
    chunks: Sequence[ChunkRecord],
    queries: Sequence[SearchQuery],
    judgments: Sequence[ChunkRelevanceJudgment],
    provider: EmbeddingProvider,
    spec: EmbeddingSpec,
    *,
    k: int = 5,
) -> list[BenchmarkResult]:
    """Measure lexical, vector, and RRF retrieval against common chunk qrels."""

    lexical = LocalBM25Retriever(chunks)
    embedded_chunks = embed_chunks(chunks, provider, spec)
    vector = LocalVectorRetriever(embedded_chunks)
    hybrid = HybridRetriever(lexical, vector)
    query_embeddings = provider.embed([query.query for query in queries])
    methods = {
        "lexical": lambda query, vector_value: lexical.search(query.query, limit=k),
        "vector": lambda query, vector_value: vector.search(vector_value, limit=k),
        "rrf": lambda query, vector_value: hybrid.search(query.query, vector_value, limit=k),
    }
    results: list[BenchmarkResult] = []
    for name, retrieve in methods.items():
        per_query: dict[str, list[SearchResult]] = {}
        started = perf_counter()
        for query, query_embedding in zip(queries, query_embeddings):
            per_query[query.query_id] = retrieve(query, query_embedding)
        elapsed_ms = (perf_counter() - started) * 1_000 / len(queries)
        results.append(BenchmarkResult(name, evaluate(per_query, judgments, k=k), elapsed_ms))
    return results


def markdown_report(results: Sequence[BenchmarkResult], *, k: int) -> str:
    """Render a compact, clearly synthetic benchmark report."""

    rows = [
        "# Synthetic retrieval benchmark",
        "",
        "These measurements use only the repository's fictional corpus; they are not production "
        "performance claims.",
        "",
        f"| Configuration | Recall@{k} | MRR@{k} | nDCG@{k} | Mean retrieval latency (ms) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    rows.extend(
        f"| {item.name} | {item.metrics.recall:.3f} | {item.metrics.mrr:.3f} | "
        f"{item.metrics.ndcg:.3f} | {item.mean_latency_ms:.3f} |"
        for item in results
    )
    return "\n".join(rows) + "\n"
