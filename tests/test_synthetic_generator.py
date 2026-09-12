import json
from pathlib import Path

from agent_search.corpus.generator import build_source_files, generate_fixtures


def test_ingestion_loads_raw_source_files() -> None:
    source_files = build_source_files()

    assert len(source_files) == 7
    assert {source_file.domain.value for source_file in source_files} == {"location", "news"}
    assert all(source_file.content_sha256 for source_file in source_files)


def test_generator_writes_file_level_records_and_evaluation_fixtures(tmp_path: Path) -> None:
    generate_fixtures(output_directory=tmp_path)

    files = [json.loads(line) for line in (tmp_path / "files.jsonl").read_text().splitlines()]
    chunks = [json.loads(line) for line in (tmp_path / "chunks.jsonl").read_text().splitlines()]
    queries = [json.loads(line) for line in (tmp_path / "queries.jsonl").read_text().splitlines()]
    judgments = [json.loads(line) for line in (tmp_path / "qrels.jsonl").read_text().splitlines()]

    assert len(files) == 7
    assert chunks
    assert all(chunk["text"] for chunk in chunks)
    assert len(queries) == 6
    assert len(judgments) == 11
    assert all(record["schema_version"] == "1.0" for record in [*files, *queries, *judgments])
