"""Deterministically partition source files into provenance-preserving chunks.

Chunk offsets are relative to ``SourceFile.body``: offset zero is the first
character after raw-file front matter has been parsed and surrounding body
whitespace has been stripped by :func:`parse_raw_file`.  Consequently,
``chunk.text == source_file.body[chunk.character_start:chunk.character_end]``
for every emitted chunk.
"""

import re

from agent_search.corpus.schemas import ChunkRecord, SourceFile

DEFAULT_TARGET_CHARACTERS = 1_100
DEFAULT_OVERLAP_CHARACTERS = 200

# The end of a blank-line separator is a paragraph boundary. Sentence endings
# intentionally cover common Latin and Korean terminal punctuation.
PARAGRAPH_BOUNDARY = re.compile(r"\n[ \t]*\n+")
SENTENCE_BOUNDARY = re.compile(r"[.!?。！？](?=\s|$)")


def _preferred_boundaries(text: str) -> list[int]:
    """Return stable paragraph-then-sentence boundary offsets for ``text``."""

    boundaries = {match.end() for match in PARAGRAPH_BOUNDARY.finditer(text)}
    boundaries.update(match.end() for match in SENTENCE_BOUNDARY.finditer(text))
    boundaries.add(len(text))
    return sorted(boundaries)


def _last_boundary_before(boundaries: list[int], start: int, limit: int) -> int | None:
    """Choose the furthest valid boundary after ``start`` and at or before ``limit``."""

    candidates = [boundary for boundary in boundaries if start < boundary <= limit]
    return candidates[-1] if candidates else None


def _overlap_start(boundaries: list[int], end: int, overlap_characters: int) -> int:
    """Choose a natural boundary near the requested overlap, or use its offset."""

    desired_start = end - overlap_characters
    # Keep the normal overlap in a narrow, readable 150--250-character range.
    natural_start = _last_boundary_before(boundaries, end - 250, end - 150)
    return natural_start if natural_start is not None else desired_start


def partition_source_file(
    source_file: SourceFile,
    *,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
    overlap_characters: int = DEFAULT_OVERLAP_CHARACTERS,
) -> list[ChunkRecord]:
    """Partition one source deterministically, preferring paragraphs then sentences.

    A chunk ends at the furthest preferred boundary within the target window.
    When an unusually long sentence has no such boundary, it is hard-split at
    the target length.  Successive chunks overlap by approximately 200
    characters, preserving complete body coverage and stable provenance.
    """

    if target_characters <= 0:
        raise ValueError("target_characters must be greater than zero")
    if not 0 <= overlap_characters < target_characters:
        raise ValueError("overlap_characters must be non-negative and less than target_characters")

    body = source_file.body
    boundaries = _preferred_boundaries(body)
    chunks: list[ChunkRecord] = []
    start = 0

    while start < len(body):
        limit = min(start + target_characters, len(body))
        end = _last_boundary_before(boundaries, start, limit) or limit
        sequence = len(chunks)
        chunks.append(
            ChunkRecord(
                chunk_id=f"{source_file.file_id}-chunk-{sequence:03d}",
                file_id=source_file.file_id,
                domain=source_file.domain,
                language=source_file.language,
                source_title=source_file.title,
                source_url=source_file.source_url,
                text=body[start:end],
                sequence=sequence,
                character_start=start,
                character_end=end,
                published_at=source_file.published_at,
                metadata=source_file.metadata.model_copy(deep=True),
            )
        )
        if end == len(body):
            break
        start = _overlap_start(boundaries, end, overlap_characters)

    return chunks


def partition_source_files(source_files: list[SourceFile]) -> list[ChunkRecord]:
    """Partition source files in their existing stable order."""

    return [chunk for source_file in source_files for chunk in partition_source_file(source_file)]
