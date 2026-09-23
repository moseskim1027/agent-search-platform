from agent_search.corpus.embeddings import embed_chunks
from agent_search.corpus.generator import build_source_files
from agent_search.corpus.opensearch_ingestion import OpenSearchChunkIngester, promote_alias
from agent_search.corpus.partitioning import partition_source_files
from agent_search.retrieval.semantic import EmbeddingSpec, HashEmbeddingProvider


class FakeIndices:
    def __init__(self) -> None:
        self.body: dict[str, object] | None = None

    def update_aliases(self, *, body: dict[str, object]) -> None:
        self.body = body


class FakeClient:
    def __init__(self) -> None:
        self.sources: dict[str, dict[str, object]] = {}
        self.bulk_actions: list[dict[str, object]] = []
        self.indices = FakeIndices()

    def mget(self, *, index: str, body: dict[str, object]) -> dict[str, object]:
        return {
            "docs": [
                {
                    "_id": chunk_id,
                    "found": chunk_id in self.sources,
                    "_source": self.sources.get(chunk_id),
                }
                for chunk_id in body["ids"]  # type: ignore[index]
            ]
        }

    def bulk(self, *, body: list[dict[str, object]], request_timeout: float) -> dict[str, object]:
        self.bulk_actions.extend(body)
        for action, source in zip(body[::2], body[1::2]):
            self.sources[action["index"]["_id"]] = source  # type: ignore[index]
        return {"errors": False}


def test_ingester_indexes_changed_chunks_then_skips_the_same_contract() -> None:
    provider = HashEmbeddingProvider(dimensions=32)
    chunks = embed_chunks(
        partition_source_files(build_source_files()),
        provider,
        EmbeddingSpec(model="test-hash", dimensions=32, version="test-hash-v1"),
    )
    client = FakeClient()
    ingester = OpenSearchChunkIngester(
        client, index="chunks-v1", dimensions=32, embedding_version="test-hash-v1", batch_size=2
    )

    first = ingester.ingest(chunks)
    second = ingester.ingest(chunks)

    assert first.indexed == len(chunks)
    assert first.unchanged == 0
    assert second.indexed == 0
    assert second.unchanged == len(chunks)
    assert client.bulk_actions[0] == {"index": {"_id": chunks[0].chunk_id}}
    assert client.bulk_actions[1]["ingestion_version"] == "1"  # type: ignore[index]


def test_alias_promotion_is_atomic() -> None:
    client = FakeClient()

    promote_alias(client, alias="agent-search-chunks-current", index="agent-search-chunks-v2")

    assert client.indices.body == {
        "actions": [
            {
                "remove": {
                    "index": "*",
                    "alias": "agent-search-chunks-current",
                    "must_exist": False,
                }
            },
            {
                "add": {
                    "index": "agent-search-chunks-v2",
                    "alias": "agent-search-chunks-current",
                    "is_write_index": True,
                }
            },
        ]
    }
