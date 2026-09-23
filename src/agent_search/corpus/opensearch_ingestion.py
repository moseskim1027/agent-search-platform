"""Resumable, idempotent bulk ingestion of embedded chunks into OpenSearch."""

import argparse
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from agent_search.app.config import Settings, get_settings
from agent_search.corpus.embeddings import load_jsonl
from agent_search.corpus.repository import INGESTION_VERSION
from agent_search.corpus.schemas import ChunkRecord


class OpenSearchIngestionError(RuntimeError):
    """Raised when a bulk ingest or release promotion cannot complete safely."""


class OpenSearchBulkClient(Protocol):
    """Small OpenSearch API surface used by the ingestion worker."""

    def mget(self, *, index: str, body: dict[str, object]) -> dict[str, object]: ...

    def bulk(
        self, *, body: list[dict[str, object]], request_timeout: float, refresh: str
    ) -> dict[str, object]: ...


@dataclass(frozen=True)
class IngestionReport:
    """A concise, log-safe summary for an ingestion run."""

    received: int
    indexed: int
    unchanged: int


class OpenSearchChunkIngester:
    """Index only chunks whose embedding or provenance contract changed."""

    def __init__(
        self,
        client: OpenSearchBulkClient,
        *,
        index: str,
        dimensions: int,
        embedding_version: str,
        batch_size: int = 250,
        request_timeout_seconds: float = 30.0,
    ) -> None:
        self.client = client
        self.index = index
        self.dimensions = dimensions
        self.embedding_version = embedding_version
        self.batch_size = batch_size
        self.request_timeout_seconds = request_timeout_seconds

    def ingest(self, chunks: Iterable[ChunkRecord]) -> IngestionReport:
        """Idempotently index valid chunks, skipping documents with the same contract."""

        records = list(chunks)
        self._validate(records)
        indexed = unchanged = 0
        for batch in _batches(records, self.batch_size):
            existing = self._existing(batch)
            changed = [
                chunk for chunk in batch if self._is_changed(chunk, existing.get(chunk.chunk_id))
            ]
            unchanged += len(batch) - len(changed)
            if changed:
                self._bulk_index(changed)
                indexed += len(changed)
        return IngestionReport(received=len(records), indexed=indexed, unchanged=unchanged)

    def _validate(self, chunks: Sequence[ChunkRecord]) -> None:
        for chunk in chunks:
            if chunk.embedding is None or len(chunk.embedding) != self.dimensions:
                raise OpenSearchIngestionError(
                    f"chunk {chunk.chunk_id} does not have a {self.dimensions}-dimension embedding"
                )
            if chunk.embedding_version != self.embedding_version:
                message = (
                    f"chunk {chunk.chunk_id} does not match embedding version "
                    f"{self.embedding_version}"
                )
                raise OpenSearchIngestionError(
                    message
                )

    def _existing(self, chunks: Sequence[ChunkRecord]) -> dict[str, dict[str, object]]:
        response = self.client.mget(
            index=self.index, body={"ids": [chunk.chunk_id for chunk in chunks]}
        )
        documents = response.get("docs", [])
        return {
            str(document["_id"]): dict(document.get("_source", {}))
            for document in documents  # type: ignore[union-attr]
            if document.get("found")
        }

    @staticmethod
    def _is_changed(chunk: ChunkRecord, stored: dict[str, object] | None) -> bool:
        if stored is None:
            return True
        return any(
            stored.get(field) != value
            for field, value in {
                "content_sha256": chunk.content_sha256,
                "embedding_model": chunk.embedding_model,
                "embedding_version": chunk.embedding_version,
                "embedding_content_sha256": chunk.embedding_content_sha256,
            }.items()
        )

    def _bulk_index(self, chunks: Sequence[ChunkRecord]) -> None:
        actions: list[dict[str, object]] = []
        for chunk in chunks:
            actions.extend(
                [
                    {"index": {"_index": self.index, "_id": chunk.chunk_id}},
                    {**chunk.model_dump(mode="json"), "ingestion_version": INGESTION_VERSION},
                ]
            )
        response = self.client.bulk(
            body=actions, request_timeout=self.request_timeout_seconds, refresh="wait_for"
        )
        if response.get("errors"):
            raise OpenSearchIngestionError("OpenSearch rejected one or more bulk indexing actions")


def promote_alias(client: Any, *, alias: str, index: str) -> None:
    """Atomically point an alias at a fully populated versioned index."""

    client.indices.update_aliases(
        body={
            "actions": [
                {"remove": {"index": "*", "alias": alias, "must_exist": False}},
                {"add": {"index": index, "alias": alias, "is_write_index": True}},
            ]
        }
    )


def _batches(records: Sequence[ChunkRecord], size: int) -> Iterable[Sequence[ChunkRecord]]:
    for start in range(0, len(records), size):
        yield records[start : start + size]


def _client(settings: Settings) -> Any:
    if not settings.opensearch_url:
        raise SystemExit("OPENSEARCH_URL is required for OpenSearch ingestion.")
    from opensearchpy import OpenSearch

    return OpenSearch(
        hosts=[settings.opensearch_url],
        http_auth=(
            (settings.opensearch_username, settings.opensearch_password.get_secret_value())
            if settings.opensearch_username and settings.opensearch_password
            else None
        ),
        use_ssl=settings.opensearch_url.startswith("https://"),
        verify_certs=settings.opensearch_verify_certs,
    )


def main() -> None:
    """Ingest an embedded JSONL artifact, optionally promoting a tested alias."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/derived/chunks.embedded.jsonl"))
    parser.add_argument("--promote-alias", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    client = _client(settings)
    report = OpenSearchChunkIngester(
        client,
        index=settings.opensearch_index,
        dimensions=settings.embedding_dimensions,
        embedding_version=settings.embedding_version,
        batch_size=settings.opensearch_ingestion_batch_size,
    ).ingest(load_jsonl(args.input))
    if args.promote_alias:
        if not settings.opensearch_write_alias:
            raise SystemExit("OPENSEARCH_WRITE_ALIAS is required with --promote-alias.")
        promote_alias(
            client, alias=settings.opensearch_write_alias, index=settings.opensearch_index
        )
    print(f"received={report.received} indexed={report.indexed} unchanged={report.unchanged}")


if __name__ == "__main__":
    main()
