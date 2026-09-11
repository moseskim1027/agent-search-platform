# Architecture overview

The first version is intentionally a modular monolith: a FastAPI process with
clear package boundaries. This keeps the project readable while allowing the
retrieval and ranking layers to be evaluated independently.

```text
Raw news and location files
        |
        v
File ingestion (provenance + metadata)
        |
        v
Metadata-preserving partitioning
        |
        v
Grounded Search API --> lexical retrieval + vector retrieval --> fusion / reranking
        |
        v
Evidence-rich result contract
```

Future pull requests will add partitioning and indexing layers behind retrieval,
followed by a benchmark harness and operational instrumentation.
