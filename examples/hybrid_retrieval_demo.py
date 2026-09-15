"""Run a credential-free semantic-hybrid retrieval demonstration."""

import argparse

from agent_search.corpus.embeddings import embed_chunks
from agent_search.corpus.generator import build_source_files
from agent_search.corpus.partitioning import partition_source_files
from agent_search.retrieval.lexical import LocalBM25Retriever
from agent_search.retrieval.semantic import (
    EmbeddingSpec,
    HashEmbeddingProvider,
    HybridRetriever,
    LocalVectorRetriever,
)


def main() -> None:
    """Fuse local BM25 and deterministic test-vector rankings into grounded evidence."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="Busan cargo terminal weather delay")
    args = parser.parse_args()
    provider = HashEmbeddingProvider(dimensions=64)
    spec = EmbeddingSpec(model="demo-hash", dimensions=64, version="demo-hash-v1")
    chunks = embed_chunks(partition_source_files(build_source_files()), provider, spec)
    hybrid = HybridRetriever(LocalBM25Retriever(chunks), LocalVectorRetriever(chunks))
    results = hybrid.search(args.query, provider.embed([args.query])[0], limit=3)
    for result in results:
        print(f"{result.rank}. {result.chunk_id} | {result.source_title} | {result.source_url}")


if __name__ == "__main__":
    main()
