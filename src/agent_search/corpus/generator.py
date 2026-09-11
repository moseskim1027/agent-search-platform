"""Ingest raw Markdown files and generate deterministic evaluation fixtures."""

import argparse
import hashlib
import json
import tomllib
from collections.abc import Iterable
from pathlib import Path

from agent_search.corpus.schemas import Domain, RelevanceJudgment, SearchQuery, SourceFile

DEFAULT_RAW_DIRECTORY = Path("data/raw")
DEFAULT_OUTPUT_DIRECTORY = Path("data/derived")
FRONT_MATTER_DELIMITER = "+++"
CORE_METADATA_FIELDS = {
    "file_id",
    "domain",
    "language",
    "title",
    "published_at",
    "source_url",
}


def parse_raw_file(path: Path, raw_directory: Path) -> SourceFile:
    """Parse TOML-front-matter Markdown into a file-level record with provenance."""

    raw_text = path.read_text(encoding="utf-8")
    if not raw_text.startswith(FRONT_MATTER_DELIMITER):
        raise ValueError(f"{path} must start with TOML front matter")

    _, front_matter, body = raw_text.split(FRONT_MATTER_DELIMITER, maxsplit=2)
    parsed_metadata = tomllib.loads(front_matter)
    relative_path = path.relative_to(raw_directory).as_posix()
    metadata = {
        key: value for key, value in parsed_metadata.items() if key not in CORE_METADATA_FIELDS
    }

    return SourceFile(
        **{key: value for key, value in parsed_metadata.items() if key in CORE_METADATA_FIELDS},
        source_path=relative_path,
        raw_text=raw_text,
        body=body.strip(),
        content_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        metadata=metadata,
    )


def build_source_files(raw_directory: Path = DEFAULT_RAW_DIRECTORY) -> list[SourceFile]:
    """Ingest every Markdown source file in stable path order."""

    paths = sorted(path for path in raw_directory.glob("*/*.md") if path.is_file())
    return [parse_raw_file(path, raw_directory) for path in paths]


def build_queries() -> list[SearchQuery]:
    """Return bilingual queries that exercise source, domain, and metadata retrieval."""

    return [
        SearchQuery(
            query_id="q-late-blue-line", query="late evening Blue Line trains", language="en"
        ),
        SearchQuery(query_id="q-busan-weather", query="Busan port weather delay", language="en"),
        SearchQuery(
            query_id="q-accessible-transfer", query="accessible Blue Line transfer", language="en"
        ),
        SearchQuery(query_id="q-night-shuttle", query="서울 심야 셔틀", language="ko"),
        SearchQuery(query_id="q-battery-recycling", query="오빗 배터리 재활용", language="ko"),
        SearchQuery(
            query_id="q-cargo-gate-times",
            query="cargo terminal gate times",
            language="en",
            domain=Domain.LOCATION,
        ),
    ]


def build_judgments() -> list[RelevanceJudgment]:
    """Return graded query-file labels before later chunk-level evaluation."""

    return [
        RelevanceJudgment(
            query_id="q-late-blue-line", file_id="news-han-river-night-service", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-late-blue-line", file_id="location-central-station", relevance=2
        ),
        RelevanceJudgment(
            query_id="q-busan-weather", file_id="news-busan-port-weather-delay", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-busan-weather", file_id="location-busan-north-terminal", relevance=2
        ),
        RelevanceJudgment(
            query_id="q-accessible-transfer", file_id="location-central-station", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-accessible-transfer", file_id="news-han-river-night-service", relevance=1
        ),
        RelevanceJudgment(
            query_id="q-night-shuttle", file_id="news-seoul-mobility-shuttle-ko", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-night-shuttle", file_id="location-riverside-park", relevance=2
        ),
        RelevanceJudgment(
            query_id="q-battery-recycling", file_id="news-orbit-battery-center-ko", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-cargo-gate-times", file_id="location-busan-north-terminal", relevance=3
        ),
        RelevanceJudgment(
            query_id="q-cargo-gate-times", file_id="news-busan-port-weather-delay", relevance=1
        ),
    ]


def write_jsonl(
    records: Iterable[SourceFile | SearchQuery | RelevanceJudgment], path: Path
) -> None:
    """Write records as stable, newline-delimited JSON for source-control-friendly diffs."""

    serialized_records = [
        json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for record in records
    ]
    path.write_text("\n".join(serialized_records) + "\n", encoding="utf-8")


def generate_fixtures(
    raw_directory: Path = DEFAULT_RAW_DIRECTORY,
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
) -> None:
    """Generate file records and evaluation fixtures from immutable raw inputs."""

    output_directory.mkdir(parents=True, exist_ok=True)
    write_jsonl(build_source_files(raw_directory), output_directory / "files.jsonl")
    write_jsonl(build_queries(), output_directory / "queries.jsonl")
    write_jsonl(build_judgments(), output_directory / "qrels.jsonl")


def parse_args() -> argparse.Namespace:
    """Parse raw and output directories for the ingestion command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIRECTORY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_fixtures(args.raw_dir, args.output_dir)
