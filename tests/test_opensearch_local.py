"""Credential-free OpenSearch smoke test against the local Docker engine."""

import json
import os
from pathlib import Path

import pytest
from opensearchpy import OpenSearch

from agent_search.corpus.embeddings import embed_chunks
from agent_search.corpus.generator import build_source_files
from agent_search.corpus.opensearch_ingestion import OpenSearchChunkIngester, promote_alias
from agent_search.corpus.partitioning import partition_source_files
from agent_search.corpus.schemas import Domain, SearchFilters
from agent_search.retrieval.opensearch import OpenSearchVectorSearchAdapter
from agent_search.retrieval.semantic import EmbeddingSpec, HashEmbeddingProvider

pytestmark = [pytest.mark.integration, pytest.mark.opensearch_local]

INDEX_DEFINITION = Path(__file__).parents[1] / "infra/opensearch/chunks-v1.index.json"
INDEX = "agent-search-opensearch-integration-test"
ALIAS = "agent-search-opensearch-integration-current"


@pytest.mark.skipif(not os.getenv("OPENSEARCH_LOCAL_URL"), reason="OPENSEARCH_LOCAL_URL is not set")
def test_real_opensearch_ingestion_alias_and_filtered_knn_retrieval() -> None:
    """Exercise the checked-in mapping, bulk worker, alias release, and k-NN adapter."""

    client = OpenSearch(hosts=[os.environ["OPENSEARCH_LOCAL_URL"]], use_ssl=False)
    provider = HashEmbeddingProvider(dimensions=768)
    spec = EmbeddingSpec(model="test-hash", dimensions=768, version="test-hash-768-v1")
    chunks = embed_chunks(partition_source_files(build_source_files()), provider, spec)
    definition = json.loads(INDEX_DEFINITION.read_text(encoding="utf-8"))

    try:
        client.indices.delete(index=INDEX, ignore=[404])
        client.indices.create(index=INDEX, body=definition)
        report = OpenSearchChunkIngester(
            client,
            index=INDEX,
            dimensions=768,
            embedding_version=spec.version,
            batch_size=2,
        ).ingest(chunks)
        assert report.indexed == len(chunks)

        promote_alias(client, alias=ALIAS, index=INDEX)
        results = OpenSearchVectorSearchAdapter(client, index=ALIAS).search(
            provider.embed(["Busan cargo terminal weather"])[0],
            SearchFilters(domain=Domain.LOCATION, region="busan"),
            limit=3,
        )

        assert results
        assert all(result.domain == Domain.LOCATION for result in results)
        assert all(result.metadata.region == "busan" for result in results)
        assert all(result.text and result.source_url for result in results)
    finally:
        client.indices.delete(index=INDEX, ignore=[404])
        client.close()
