"""Optional live MongoDB test; enabled only when MONGODB_URI is configured."""

import os

import pytest
from pymongo import MongoClient

from agent_search.corpus.generator import build_source_files
from agent_search.corpus.partitioning import partition_source_files
from agent_search.corpus.repository import MongoCorpusRepository

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("MONGODB_URI"), reason="MONGODB_URI is not configured")
def test_repository_upserts_generated_records_to_local_mongodb() -> None:
    """Write generated data twice to prove local MongoDB upserts are idempotent."""

    client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=5_000)
    database = client["agent_search_integration_test"]
    repository = MongoCorpusRepository(database)
    source_files = build_source_files()
    chunks = partition_source_files(source_files)

    try:
        assert client.admin.command("ping")["ok"] == 1.0
        assert repository.upsert_source_files(source_files) == len(source_files)
        assert repository.upsert_chunks(chunks) == len(chunks)
        assert repository.upsert_source_files(source_files) == len(source_files)
        assert repository.upsert_chunks(chunks) == len(chunks)
        assert database["source_files"].count_documents({}) == len(source_files)
        assert database["chunks"].count_documents({}) == len(chunks)
    finally:
        client.drop_database(database.name)
        client.close()
