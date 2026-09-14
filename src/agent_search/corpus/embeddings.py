"""Resumable embedding generation for derived chunk records."""

import argparse
import json
import ssl
from collections.abc import Iterable, Sequence
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import certifi

from agent_search.app.config import get_settings
from agent_search.corpus.schemas import ChunkRecord
from agent_search.retrieval.semantic import EmbeddingSpec


class EmbeddingProvider:
    """Minimal provider interface to keep generation separate from a vendor SDK."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding per supplied text."""  # pragma: no cover - protocol method
        raise NotImplementedError


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Small standard-library client for Gemini embeddings, used only by the CLI."""

    def __init__(self, api_key: str, spec: EmbeddingSpec) -> None:
        self.api_key = api_key
        self.spec = spec

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(self.spec.model, safe='')}:embedContent"
        )
        for text in texts:
            payload = json.dumps(
                {
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": self.spec.dimensions,
                }
            ).encode("utf-8")
            request = Request(
                endpoint,
                data=payload,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                method="POST",
            )
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            with urlopen(  # noqa: S310 - fixed Gemini endpoint with verified CA bundle
                request, timeout=60, context=ssl_context
            ) as response:
                data = json.load(response)
            vector = data["embedding"]["values"]
            if len(vector) != self.spec.dimensions:
                raise ValueError("embedding provider returned unexpected dimensions")
            vectors.append(vector)
        return vectors


def embed_chunks(
    chunks: Iterable[ChunkRecord], provider: EmbeddingProvider, spec: EmbeddingSpec
) -> list[ChunkRecord]:
    """Embed only chunks whose content or embedding contract has changed."""

    records = list(chunks)
    stale = [
        chunk
        for chunk in records
        if chunk.embedding is None
        or chunk.embedding_model != spec.model
        or chunk.embedding_version != spec.version
        or chunk.embedding_content_sha256 != chunk.content_sha256
    ]
    vectors = provider.embed([chunk.text for chunk in stale])
    if len(vectors) != len(stale):
        raise ValueError("embedding provider returned an unexpected vector count")
    updates = {
        chunk.chunk_id: chunk.model_copy(
            update={
                "embedding": vector,
                "embedding_model": spec.model,
                "embedding_version": spec.version,
                "embedding_content_sha256": chunk.content_sha256,
            }
        )
        for chunk, vector in zip(stale, vectors)
    }
    return [updates.get(chunk.chunk_id, chunk) for chunk in records]


def load_jsonl(path: Path) -> list[ChunkRecord]:
    """Load generated chunks for the embedding command."""

    return [ChunkRecord.model_validate_json(line) for line in path.read_text().splitlines() if line]


def write_jsonl(chunks: Iterable[ChunkRecord], path: Path) -> None:
    """Persist embedded chunks without changing the raw corpus."""

    path.write_text(
        "\n".join(
            json.dumps(chunk.model_dump(mode="json"), sort_keys=True) for chunk in chunks
        )
        + "\n"
    )


def main() -> None:
    """Embed a generated corpus using the configured Gemini API key."""

    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/derived/chunks.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/chunks.embedded.jsonl"))
    parser.add_argument("--model", default=settings.embedding_model)
    parser.add_argument("--dimensions", type=int, default=settings.embedding_dimensions)
    parser.add_argument("--version", default=settings.embedding_version)
    args = parser.parse_args()
    if settings.gemini_api_key is None:
        raise SystemExit("GEMINI_API_KEY is required to generate embeddings.")
    api_key = settings.gemini_api_key.get_secret_value()
    spec = EmbeddingSpec(
        model=args.model,
        dimensions=args.dimensions,
        version=args.version,
    )
    embedded = embed_chunks(load_jsonl(args.input), GeminiEmbeddingProvider(api_key, spec), spec)
    write_jsonl(embedded, args.output)


if __name__ == "__main__":
    main()
