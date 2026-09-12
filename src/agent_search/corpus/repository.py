"""Idempotent MongoDB persistence for generated source and chunk records."""

from collections.abc import Iterable

from pymongo import UpdateOne
from pymongo.database import Database

from agent_search.corpus.schemas import ChunkRecord, SourceFile

INGESTION_VERSION = "1"


class MongoCorpusRepository:
    """Persist generated records without coupling generation to a live client."""

    def __init__(
        self,
        database: Database,
        *,
        source_files_collection: str = "source_files",
        chunks_collection: str = "chunks",
        ingestion_version: str = INGESTION_VERSION,
    ) -> None:
        self.source_files = database[source_files_collection]
        self.chunks = database[chunks_collection]
        self.ingestion_version = ingestion_version

    def upsert_source_files(self, source_files: Iterable[SourceFile]) -> int:
        """Upsert source files by ID and return the number of matched/upserted writes."""

        operations = [
            UpdateOne(
                {"file_id": source_file.file_id},
                {"$set": self._document(source_file)},
                upsert=True,
            )
            for source_file in source_files
        ]
        return self._bulk_upsert(self.source_files, operations)

    def upsert_chunks(self, chunks: Iterable[ChunkRecord]) -> int:
        """Upsert chunks by ID and return the number of matched/upserted writes."""

        operations = [
            UpdateOne(
                {"chunk_id": chunk.chunk_id},
                {"$set": self._document(chunk)},
                upsert=True,
            )
            for chunk in chunks
        ]
        return self._bulk_upsert(self.chunks, operations)

    def _document(self, record: SourceFile | ChunkRecord) -> dict[str, object]:
        """Serialize a record with explicit ingestion provenance for idempotent writes."""

        return {
            **record.model_dump(mode="json"),
            "ingestion_version": self.ingestion_version,
        }

    @staticmethod
    def _bulk_upsert(collection: object, operations: list[UpdateOne]) -> int:
        """Avoid an unnecessary MongoDB call when no records were supplied."""

        if not operations:
            return 0
        result = collection.bulk_write(operations, ordered=False)  # type: ignore[attr-defined]
        return result.matched_count + result.upserted_count
