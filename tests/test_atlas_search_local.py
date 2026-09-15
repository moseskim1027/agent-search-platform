"""Optional smoke test for the Atlas Search adapter against Atlas Local."""

import json
import os
import time
from pathlib import Path

import pytest
from pymongo import MongoClient

from agent_search.corpus.embeddings import embed_chunks
from agent_search.corpus.generator import build_source_files
from agent_search.corpus.partitioning import partition_source_files
from agent_search.corpus.repository import MongoCorpusRepository
from agent_search.corpus.schemas import Domain, SearchFilters
from agent_search.retrieval.lexical import AtlasSearchAdapter
from agent_search.retrieval.semantic import (
    AtlasVectorSearchAdapter,
    EmbeddingSpec,
    HashEmbeddingProvider,
)

pytestmark = [pytest.mark.integration, pytest.mark.atlas_local]

INDEX_DEFINITION = Path(__file__).parents[1] / "infra/mongodb/chunks.atlas-search-index.json"
VECTOR_INDEX_DEFINITION = (
    Path(__file__).parents[1] / "infra/mongodb/chunks.vector-search-index.json"
)


@pytest.mark.skipif(not os.getenv("ATLAS_LOCAL_URI"), reason="ATLAS_LOCAL_URI is not configured")
def test_atlas_search_adapter_retrieves_filtered_grounded_chunks() -> None:
    """Create the checked-in index, then execute the adapter's real $search pipeline."""

    client = MongoClient(os.environ["ATLAS_LOCAL_URI"], serverSelectionTimeoutMS=10_000)
    database = client["agent_search_atlas_local_test"]
    chunks = partition_source_files(build_source_files())
    index = json.loads(INDEX_DEFINITION.read_text(encoding="utf-8"))

    try:
        _wait_for_writable_primary(client)
        MongoCorpusRepository(database).upsert_chunks(chunks)
        database.command(
            {
                "createSearchIndexes": "chunks",
                "indexes": [{"name": index["name"], "definition": index["definition"]}],
            }
        )
        _wait_for_search_index(database, index["name"])

        pipeline = AtlasSearchAdapter().pipeline(
            "cargo terminal weather",
            SearchFilters(domain=Domain.LOCATION, region="busan"),
            limit=5,
        )
        results = list(database["chunks"].aggregate(pipeline))

        assert results
        assert all(result["domain"] == "location" for result in results)
        assert all(result["metadata"]["region"] == "busan" for result in results)
        assert all(result["text"] and result["source_url"] for result in results)
    finally:
        client.drop_database(database.name)
        client.close()


@pytest.mark.skipif(not os.getenv("ATLAS_LOCAL_URI"), reason="ATLAS_LOCAL_URI is not configured")
def test_atlas_vector_adapter_retrieves_filtered_grounded_chunks() -> None:
    client = MongoClient(os.environ["ATLAS_LOCAL_URI"], serverSelectionTimeoutMS=10_000)
    database = client["agent_search_atlas_local_vector_test"]
    provider = HashEmbeddingProvider(dimensions=768)
    spec = EmbeddingSpec(model="test-hash", dimensions=768, version="test-hash-768-v1")
    chunks = embed_chunks(partition_source_files(build_source_files()), provider, spec)
    index = json.loads(VECTOR_INDEX_DEFINITION.read_text(encoding="utf-8"))
    try:
        _wait_for_writable_primary(client)
        MongoCorpusRepository(database).upsert_chunks(chunks)
        database.command(
            {
                "createSearchIndexes": "chunks",
                "indexes": [
                    {
                        "name": index["name"],
                        "type": index["type"],
                        "definition": index["definition"],
                    }
                ],
            }
        )
        _wait_for_search_index(database, index["name"])
        pipeline = AtlasVectorSearchAdapter().pipeline(
            provider.embed(["Busan cargo terminal weather"])[0],
            SearchFilters(domain=Domain.LOCATION, region="busan"),
            limit=3,
        )
        results = list(database["chunks"].aggregate(pipeline))
        assert results
        assert all(result["domain"] == "location" for result in results)
        assert all(result["metadata"]["region"] == "busan" for result in results)
    finally:
        client.drop_database(database.name)
        client.close()


def _wait_for_search_index(database: object, name: str) -> None:
    """Wait briefly for Atlas Local's asynchronous index build to become queryable."""

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        indexes = list(database["chunks"].aggregate([{"$listSearchIndexes": {"name": name}}]))  # type: ignore[index]
        if indexes and indexes[0].get("status") == "READY":
            return
        time.sleep(1)
    raise AssertionError(f"Atlas Search index {name!r} did not become ready")


def _wait_for_writable_primary(client: MongoClient) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if client.admin.command("hello").get("isWritablePrimary"):
                return
        except Exception:
            pass
        time.sleep(1)
    raise AssertionError("Atlas Local did not become a writable primary")
