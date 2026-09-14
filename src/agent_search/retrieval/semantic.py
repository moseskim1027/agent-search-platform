"""Dependency-free vector retrieval, embedding contracts, and rank fusion."""

import hashlib
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from agent_search.corpus.schemas import ChunkRecord, SearchFilters, SearchResult
from agent_search.retrieval.lexical import _tokens, matches_filters


@dataclass(frozen=True)
class EmbeddingSpec:
    """A versioned embedding model contract stored with every generated vector."""

    model: str = "gemini-embedding-2"
    dimensions: int = 768
    version: str = "gemini-embedding-2-768-l2-v1"
    normalization: str = "l2"


class HashEmbeddingProvider:
    """Deterministic test-only embedder; never use this provider for production data."""

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in _tokens(text):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimensions
                vector[index] += -1.0 if digest[4] & 1 else 1.0
            vectors.append(normalize(vector))
        return vectors


def normalize(vector: Sequence[float]) -> list[float]:
    """Return an L2-normalized vector, preserving a zero vector when supplied."""

    magnitude = math.sqrt(sum(value * value for value in vector))
    return [value / magnitude for value in vector] if magnitude else list(vector)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Calculate cosine similarity and reject mismatched stored embeddings."""

    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    left_normalized = normalize(left)
    right_normalized = normalize(right)
    return sum(a * b for a, b in zip(left_normalized, right_normalized))


class LocalVectorRetriever:
    """In-memory vector search with the same filters and evidence contract as BM25."""

    def __init__(self, chunks: Iterable[ChunkRecord]) -> None:
        self.chunks = list(chunks)

    def search(
        self,
        query_embedding: Sequence[float],
        filters: SearchFilters | None = None,
        *,
        limit: int = 10,
    ) -> list[SearchResult]:
        if limit < 1:
            return []
        active_filters = filters or SearchFilters()
        scored: list[tuple[float, ChunkRecord]] = []
        for chunk in self.chunks:
            if chunk.embedding is None or not matches_filters(chunk, active_filters):
                continue
            score = cosine_similarity(query_embedding, chunk.embedding)
            scored.append((score, chunk))
        return [
            _search_result(rank, score, chunk)
            for rank, (score, chunk) in enumerate(
                sorted(scored, key=lambda item: (-item[0], item[1].chunk_id))[:limit], start=1
            )
        ]


class HybridRetriever:
    """Run lexical and vector retrieval independently, then fuse their rankings."""

    def __init__(self, lexical: object, vector: LocalVectorRetriever, *, rrf_k: int = 60) -> None:
        self.lexical = lexical
        self.vector = vector
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        query_embedding: Sequence[float],
        filters: SearchFilters | None = None,
        *,
        limit: int = 10,
        candidate_limit: int = 50,
    ) -> list[SearchResult]:
        """Return stable RRF results while allowing callers to inspect each retriever alone."""

        lexical_results = self.lexical.search(query, filters, limit=candidate_limit)
        vector_results = self.vector.search(query_embedding, filters, limit=candidate_limit)
        return reciprocal_rank_fusion(lexical_results, vector_results, k=self.rrf_k)[:limit]


def reciprocal_rank_fusion(
    lexical_results: Sequence[SearchResult], vector_results: Sequence[SearchResult], *, k: int = 60
) -> list[SearchResult]:
    """Fuse independently ranked lists with stable IDs as the tie breaker."""

    if k < 1:
        raise ValueError("k must be positive")
    combined: dict[str, tuple[float, SearchResult]] = {}
    for results in (lexical_results, vector_results):
        for result in results:
            score, evidence = combined.get(result.chunk_id, (0.0, result))
            combined[result.chunk_id] = (score + 1 / (k + result.rank), evidence)
    return [
        evidence.model_copy(update={"rank": rank, "score": score})
        for rank, (_, (score, evidence)) in enumerate(
            sorted(combined.items(), key=lambda item: (-item[1][0], item[0])), start=1
        )
    ]


def _search_result(rank: int, score: float, chunk: ChunkRecord) -> SearchResult:
    return SearchResult(
        chunk_id=chunk.chunk_id,
        file_id=chunk.file_id,
        rank=rank,
        score=score,
        text=chunk.text,
        character_start=chunk.character_start,
        character_end=chunk.character_end,
        source_title=chunk.source_title,
        source_url=chunk.source_url,
        domain=chunk.domain,
        language=chunk.language,
        published_at=chunk.published_at,
        metadata=chunk.metadata,
    )
