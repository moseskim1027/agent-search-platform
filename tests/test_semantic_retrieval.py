from agent_search.corpus.embeddings import embed_chunks
from agent_search.corpus.generator import build_source_files
from agent_search.corpus.partitioning import partition_source_files
from agent_search.corpus.schemas import Domain, SearchFilters
from agent_search.retrieval.lexical import LocalBM25Retriever
from agent_search.retrieval.semantic import (
    EmbeddingSpec,
    HashEmbeddingProvider,
    HybridRetriever,
    LocalVectorRetriever,
    reciprocal_rank_fusion,
)


def embedded_chunks():
    provider = HashEmbeddingProvider(dimensions=32)
    spec = EmbeddingSpec(model="test-hash", dimensions=32, version="test-hash-v1")
    chunks = partition_source_files(build_source_files())
    return embed_chunks(chunks, provider, spec), provider, spec


def test_embedding_generation_is_resumable_and_tracks_content_version() -> None:
    chunks, provider, spec = embedded_chunks()
    repeated = embed_chunks(chunks, provider, spec)

    assert repeated == chunks
    assert all(chunk.embedding_content_sha256 == chunk.content_sha256 for chunk in repeated)


def test_vector_retrieval_returns_filtered_grounded_evidence() -> None:
    chunks, provider, _ = embedded_chunks()
    results = LocalVectorRetriever(chunks).search(
        provider.embed(["Busan cargo terminal weather"])[0],
        SearchFilters(domain=Domain.LOCATION, region="busan"),
    )

    assert results
    assert all(
        result.domain == Domain.LOCATION and result.metadata.region == "busan" for result in results
    )
    assert results[0].text and results[0].source_url


def test_rrf_is_deterministic_and_hybrid_combines_both_retrievers() -> None:
    chunks, provider, _ = embedded_chunks()
    query = "Busan cargo terminal weather"
    hybrid = HybridRetriever(LocalBM25Retriever(chunks), LocalVectorRetriever(chunks), rrf_k=20)
    results = hybrid.search(query, provider.embed([query])[0], limit=3)
    fused = reciprocal_rank_fusion(results[:1], results[1:], k=20)

    assert [result.rank for result in results] == [1, 2, 3]
    assert results[0].file_id in {"location-busan-north-terminal", "news-busan-port-weather-delay"}
    assert [result.rank for result in fused] == [1, 2, 3]
