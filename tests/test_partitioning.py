from datetime import date

import pytest

from agent_search.corpus.partitioning import partition_source_file, partition_source_files
from agent_search.corpus.schemas import Domain, GeoPoint, SearchMetadata, SourceFile


def make_source(body: str, *, language: str = "en") -> SourceFile:
    return SourceFile(
        file_id="news-partitioning-example",
        domain=Domain.NEWS,
        language=language,
        title="Synthetic partitioning example",
        source_url="https://synthetic.example/news/partitioning-example",
        source_path="news/partitioning-example.md",
        raw_text=f"+++\ntitle = 'Synthetic partitioning example'\n+++\n\n{body}",
        body=body,
        content_sha256="a" * 64,
        published_at=date(2026, 1, 1),
        metadata=SearchMetadata(
            region="seoul",
            tags=["synthetic", "partitioning"],
            category="test",
            geo=GeoPoint(coordinates=(126.9779, 37.5652)),
        ),
    )


def test_partitioning_uses_stable_ids_and_exact_body_relative_provenance() -> None:
    body = "\n\n".join(f"Paragraph {index}. " + ("detail " * 55) for index in range(8))
    source = make_source(body)

    first_run = partition_source_file(source)
    second_run = partition_source_file(source)

    assert [chunk.chunk_id for chunk in first_run] == [
        f"news-partitioning-example-chunk-{index:03d}" for index in range(len(first_run))
    ]
    assert first_run == second_run
    assert all(
        chunk.text == source.body[chunk.character_start : chunk.character_end]
        for chunk in first_run
    )


def test_partitioning_preserves_coverage_and_approximately_200_character_overlap() -> None:
    body = "\n\n".join(f"Paragraph {index}. " + ("evidence " * 70) for index in range(9))
    chunks = partition_source_file(make_source(body))

    assert len(chunks) > 1
    assert chunks[0].character_start == 0
    assert chunks[-1].character_end == len(body)
    assert all(
        next_chunk.character_start <= chunk.character_end
        for chunk, next_chunk in zip(chunks, chunks[1:])
    )
    assert all(
        150 <= chunk.character_end - next_chunk.character_start <= 250
        for chunk, next_chunk in zip(chunks, chunks[1:])
    )


def test_partitioning_handles_korean_text_and_short_sources() -> None:
    korean = "첫 문장입니다. " * 200
    korean_chunks = partition_source_file(make_source(korean, language="ko"))
    short_chunks = partition_source_file(make_source("짧은 합성 문서입니다.", language="ko"))

    assert len(korean_chunks) > 1
    assert "첫 문장입니다." in korean_chunks[0].text
    assert len(short_chunks) == 1
    assert short_chunks[0].text == "짧은 합성 문서입니다."


def test_partitioning_copies_all_source_metadata() -> None:
    source = make_source("Evidence sentence. " * 100)
    chunks = partition_source_files([source])

    assert all(chunk.file_id == source.file_id for chunk in chunks)
    assert all(chunk.domain == source.domain for chunk in chunks)
    assert all(chunk.language == source.language for chunk in chunks)
    assert all(chunk.source_title == source.title for chunk in chunks)
    assert all(chunk.source_url == source.source_url for chunk in chunks)
    assert all(chunk.published_at == source.published_at for chunk in chunks)
    assert all(chunk.metadata == source.metadata for chunk in chunks)
    assert all(chunk.metadata is not source.metadata for chunk in chunks)


def test_partitioning_hard_splits_an_exceptionally_long_sentence() -> None:
    chunks = partition_source_file(make_source("x" * 2_300))

    assert [len(chunk.text) for chunk in chunks] == [1_100, 1_100, 500]


@pytest.mark.parametrize(
    ("target_characters", "overlap_characters"), [(0, 0), (100, -1), (100, 100)]
)
def test_partitioning_rejects_invalid_window_settings(
    target_characters: int, overlap_characters: int
) -> None:
    with pytest.raises(ValueError):
        partition_source_file(
            make_source("Synthetic source."),
            target_characters=target_characters,
            overlap_characters=overlap_characters,
        )
