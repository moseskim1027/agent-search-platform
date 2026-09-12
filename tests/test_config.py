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
