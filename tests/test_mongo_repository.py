from datetime import date

from agent_search.corpus.partitioning import partition_source_file
from agent_search.corpus.repository import MongoCorpusRepository
from agent_search.corpus.schemas import Domain, SearchMetadata, SourceFile


class FakeBulkWriteResult:
    def __init__(self, *, matched_count: int, upserted_count: int) -> None:
        self.matched_count = matched_count
        self.upserted_count = upserted_count


class FakeCollection:
    def __init__(self) -> None:
        self.operations: list[object] = []

    def bulk_write(self, operations: list[object], *, ordered: bool) -> FakeBulkWriteResult:
        assert ordered is False
        self.operations.extend(operations)
        return FakeBulkWriteResult(matched_count=0, upserted_count=len(operations))


class FakeDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


def make_source() -> SourceFile:
    body = "A synthetic source document for persistence. " * 40
    return SourceFile(
        file_id="news-persistence-example",
        domain=Domain.NEWS,
        language="en",
        title="Synthetic persistence example",
        source_url="https://synthetic.example/news/persistence-example",
        source_path="news/persistence-example.md",
        raw_text=body,
        body=body,
        content_sha256="a" * 64,
        published_at=date(2026, 1, 1),
        metadata=SearchMetadata(region="seoul", tags=["synthetic"]),
    )


def test_repository_upserts_source_files_with_provenance() -> None:
    database = FakeDatabase()
    repository = MongoCorpusRepository(database, ingestion_version="test-v1")  # type: ignore[arg-type]

    assert repository.upsert_source_files([make_source()]) == 1

    operation = database["source_files"].operations[0]
    assert operation._filter == {"file_id": "news-persistence-example"}  # type: ignore[attr-defined]
    assert operation._upsert is True  # type: ignore[attr-defined]
    document = operation._doc["$set"]  # type: ignore[attr-defined]
    assert document["content_sha256"] == "a" * 64
    assert document["ingestion_version"] == "test-v1"


def test_repository_upserts_chunks_by_chunk_id_and_skips_empty_writes() -> None:
    database = FakeDatabase()
    repository = MongoCorpusRepository(database, ingestion_version="test-v1")  # type: ignore[arg-type]
    chunk = partition_source_file(make_source())[0]

    assert repository.upsert_chunks([chunk]) == 1
    assert repository.upsert_chunks([]) == 0

    operation = database["chunks"].operations[0]
    assert operation._filter == {"chunk_id": chunk.chunk_id}  # type: ignore[attr-defined]
    document = operation._doc["$set"]  # type: ignore[attr-defined]
    assert document["content_sha256"] == chunk.content_sha256
    assert document["metadata"]["region"] == "seoul"
