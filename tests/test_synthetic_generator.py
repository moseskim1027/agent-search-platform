import json
from pathlib import Path

from agent_search.corpus.generator import build_documents, generate_corpus


def test_generated_corpus_is_deterministic() -> None:
    assert build_documents() == build_documents()


def test_generator_writes_versioned_jsonl_files(tmp_path: Path) -> None:
    generate_corpus(tmp_path)

    documents = [
        json.loads(line) for line in (tmp_path / "documents.jsonl").read_text().splitlines()
    ]
    queries = [json.loads(line) for line in (tmp_path / "queries.jsonl").read_text().splitlines()]
    judgments = [json.loads(line) for line in (tmp_path / "qrels.jsonl").read_text().splitlines()]

    assert len(documents) == 10
    assert len(queries) == 6
    assert len(judgments) == 11
    assert {document["language"] for document in documents} == {"en", "ko"}
    assert all(record["schema_version"] == "1.0" for record in [*documents, *queries, *judgments])
