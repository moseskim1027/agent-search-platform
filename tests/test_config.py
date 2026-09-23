from agent_search.app.config import Settings


def test_settings_expose_explicit_mongodb_configuration() -> None:
    settings = Settings(
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="test_search",
        mongodb_source_files_collection="test_files",
        mongodb_chunks_collection="test_chunks",
    )

    assert settings.mongodb_uri == "mongodb://localhost:27017"
    assert settings.mongodb_database == "test_search"
    assert settings.mongodb_source_files_collection == "test_files"
    assert settings.mongodb_chunks_collection == "test_chunks"


def test_settings_expose_versioned_embedding_contract() -> None:
    settings = Settings()

    assert settings.embedding_model == "gemini-embedding-2"
    assert settings.embedding_dimensions == 768
    assert settings.embedding_version == "gemini-embedding-2-768-l2-v1"
    assert settings.embedding_normalization == "l2"
    assert settings.rrf_k == 60


def test_settings_accept_gemini_api_key() -> None:
    settings = Settings(gemini_api_key="test-key")

    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "test-key"


def test_opensearch_backend_requires_url_and_exposes_registry() -> None:
    settings = Settings(search_backend="opensearch", opensearch_url="https://search.example.invalid")

    assert settings.opensearch_index == "agent-search-chunks-v1"
    assert settings.opensearch_index_version == "opensearch-chunks-v1"
