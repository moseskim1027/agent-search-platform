import pytest

from agent_search.corpus.generator import build_chunk_judgments, build_queries, build_source_files
from agent_search.corpus.partitioning import partition_source_files
from agent_search.corpus.schemas import ChunkRelevanceJudgment
from agent_search.evaluation.metrics import evaluate
from agent_search.evaluation.runner import benchmark, markdown_report
from agent_search.retrieval.lexical import LocalBM25Retriever
from agent_search.retrieval.semantic import EmbeddingSpec, HashEmbeddingProvider


def test_chunk_judgments_cover_all_relevant_source_chunks() -> None:
    judgments = build_chunk_judgments()

    assert judgments
    assert {judgment.chunk_id for judgment in judgments} <= {
        chunk.chunk_id for chunk in partition_source_files(build_source_files())
    }


def test_metrics_reward_ranked_relevance() -> None:
    chunks = partition_source_files(build_source_files())
    retriever = LocalBM25Retriever(chunks)
    results = {"q-busan-weather": retriever.search("Busan port weather delay", limit=3)}
    judgments = [
        judgment for judgment in build_chunk_judgments() if judgment.query_id == "q-busan-weather"
    ]

    metrics = evaluate(results, judgments, k=3)

    assert metrics.recall > 0
    assert metrics.mrr > 0
    assert 0 < metrics.ndcg <= 1


def test_metrics_reject_invalid_cutoff() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        evaluate(
            {},
            [
                ChunkRelevanceJudgment(
                    query_id="q-busan-weather",
                    chunk_id="news-busan-port-weather-delay-chunk-000",
                    relevance=3,
                )
            ],
            k=0,
        )


def test_benchmark_compares_all_retrieval_configurations() -> None:
    chunks = partition_source_files(build_source_files())
    queries = build_queries()
    results = benchmark(
        chunks,
        queries,
        build_chunk_judgments(),
        HashEmbeddingProvider(dimensions=32),
        EmbeddingSpec(model="test-hash", dimensions=32, version="test-hash-v1"),
    )

    assert [result.name for result in results] == ["lexical", "vector", "rrf"]
    assert "Synthetic retrieval benchmark" in markdown_report(results, k=5)
