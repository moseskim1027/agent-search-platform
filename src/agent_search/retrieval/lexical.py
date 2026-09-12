"""Deterministic local BM25 retrieval and an Atlas Search-shaped adapter."""

import math
import re
from collections import Counter
from collections.abc import Iterable

from agent_search.corpus.schemas import ChunkRecord, GeographicRadius, SearchFilters, SearchResult

TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
EARTH_RADIUS_METERS = 6_371_000


def _tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _distance_meters(latitude: float, longitude: float, point: GeographicRadius) -> float:
    latitude_delta = math.radians(latitude - point.latitude)
    longitude_delta = math.radians(longitude - point.longitude)
    origin_latitude = math.radians(point.latitude)
    target_latitude = math.radians(latitude)
    a = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(origin_latitude) * math.cos(target_latitude) * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def matches_filters(chunk: ChunkRecord, filters: SearchFilters) -> bool:
    """Return whether a chunk satisfies all metadata filters."""

    if filters.domain and chunk.domain != filters.domain:
        return False
    if filters.language and chunk.language != filters.language:
        return False
    if filters.region and chunk.metadata.region != filters.region:
        return False
    if filters.tag and filters.tag not in chunk.metadata.tags:
        return False
    if filters.category and chunk.metadata.category != filters.category:
        return False
    if filters.published_from and (
        chunk.published_at is None or chunk.published_at < filters.published_from
    ):
        return False
    if filters.published_to and (
        chunk.published_at is None or chunk.published_at > filters.published_to
    ):
        return False
    if filters.geographic_radius:
        if chunk.metadata.geo is None:
            return False
        longitude, latitude = chunk.metadata.geo.coordinates
        if (
            _distance_meters(latitude, longitude, filters.geographic_radius)
            > filters.geographic_radius.radius_meters
        ):
            return False
    return True


class LocalBM25Retriever:
    """Small dependency-free BM25 baseline intended for deterministic evaluation."""

    def __init__(self, chunks: Iterable[ChunkRecord], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self.documents = [_tokens(f"{chunk.source_title} {chunk.text}") for chunk in self.chunks]
        self.lengths = [len(document) for document in self.documents]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0
        self.document_frequency = Counter(
            token for document in self.documents for token in set(document)
        )

    def search(
        self, query: str, filters: SearchFilters | None = None, *, limit: int = 10
    ) -> list[SearchResult]:
        """Rank matching chunks using BM25, with stable chunk-ID tie breaking."""

        query_tokens = _tokens(query)
        if not query_tokens or limit < 1:
            return []
        active_filters = filters or SearchFilters()
        scored: list[tuple[float, ChunkRecord]] = []
        for chunk, document, length in zip(self.chunks, self.documents, self.lengths):
            if not matches_filters(chunk, active_filters):
                continue
            frequencies = Counter(document)
            score = 0.0
            for token in query_tokens:
                frequency = frequencies[token]
                if not frequency:
                    continue
                inverse_frequency = math.log(
                    1
                    + (len(self.chunks) - self.document_frequency[token] + 0.5)
                    / (self.document_frequency[token] + 0.5)
                )
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / self.average_length
                )
                score += inverse_frequency * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scored.append((score, chunk))
        return [
            self._result(rank, score, chunk)
            for rank, (score, chunk) in enumerate(
                sorted(scored, key=lambda item: (-item[0], item[1].chunk_id))[:limit], start=1
            )
        ]

    @staticmethod
    def _result(rank: int, score: float, chunk: ChunkRecord) -> SearchResult:
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


class AtlasSearchAdapter:
    """Build a production-shaped Atlas Search pipeline without owning a client."""

    def pipeline(self, query: str, filters: SearchFilters, limit: int) -> list[dict[str, object]]:
        """Return the aggregation pipeline an Atlas-backed repository can execute."""

        filter_clauses: list[dict[str, object]] = []
        for path, value in (
            ("domain", filters.domain),
            ("language", filters.language),
            ("metadata.region", filters.region),
            ("metadata.tags", filters.tag),
            ("metadata.category", filters.category),
        ):
            if value is not None:
                filter_clauses.append({"equals": {"path": path, "value": value}})
        if filters.published_from or filters.published_to:
            range_filter: dict[str, object] = {"path": "published_at"}
            if filters.published_from:
                range_filter["gte"] = filters.published_from.isoformat()
            if filters.published_to:
                range_filter["lte"] = filters.published_to.isoformat()
            filter_clauses.append({"range": range_filter})
        return [
            {
                "$search": {
                    "index": "chunk_text_and_filters",
                    "compound": {
                        "must": [{"text": {"query": query, "path": ["text", "source_title"]}}],
                        "filter": filter_clauses,
                    },
                }
            },
            {"$limit": limit},
            {"$set": {"score": {"$meta": "searchScore"}}},
        ]
