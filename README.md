# Agent Search Platform

[![CI](https://github.com/moseskim1027/agent-search-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/moseskim1027/agent-search-platform/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/license/mit)

A production-oriented reference project for grounded, multi-domain search APIs.
It will combine lexical retrieval, vector retrieval, rank fusion, reranking, and
evidence-rich results that an AI agent can safely consume.

## Status

The reference implementation includes lexical and vector retrieval primitives,
grounded search, synthetic evaluation, and request observability. All committed
corpus artifacts are fictional.

## Architecture

```text
fictional Markdown sources
          │
          ▼
ingestion → source files → deterministic chunks → MongoDB / Atlas indexes
                              │                     │
                              ├─ BM25 lexical ──────┤
                              └─ Gemini vectors ────┤
                                                    ▼
client → FastAPI /v1/search ← RRF fusion ← ranked grounded evidence
              │
              └─ query-safe logs, metrics, ranking version
```

## Goals

- Search across news articles and location profiles.
- Make grounding explicit through source and passage metadata.
- Measure relevance with nDCG, MRR, and recall alongside latency.
- Keep the system locally runnable and production-minded.

## Data policy

This repository will use **synthetic data only** in its committed examples,
fixtures, and evaluation sets. The synthetic corpus will be clearly labelled and
generated deterministically. It is designed to exercise retrieval behavior and
API contracts, not to represent real news, company disclosures, users, clicks,
or business outcomes.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn agent_search.app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` or run:

```bash
curl http://127.0.0.1:8000/health
```

## Run with Docker

Build and start the API:

```bash
docker compose up --build
```

The service is available at `http://127.0.0.1:8000`; its container health check
calls `/health`. Stop the service with `docker compose down`.

## Continuous integration

GitHub Actions runs Ruff, the test suite, and a Docker image build for every
pull request and for changes merged to `main`.

## Project layout

```text
src/agent_search/      Application and ingestion packages
tests/                 Automated tests
data/raw/              Immutable synthetic source files
data/derived/          Generated file records and evaluation fixtures
docs/                  Architecture and decision records
```

## Chunking contract

`python -m agent_search.corpus.generator` derives `data/derived/chunks.jsonl`
alongside the file records, queries, and file-level relevance labels. Raw
Markdown is never modified. Each source body is partitioned deterministically
into roughly 1,100-character windows with approximately 200 characters of
overlap, preferring paragraph boundaries and then sentence boundaries. An
exceptionally long sentence is hard-split only when no natural boundary fits.

Chunk offsets are **body-relative**: offset zero is the first character of the
parsed, edge-whitespace-stripped `SourceFile.body`, after TOML front matter is
removed. Therefore every chunk obeys this provenance invariant:

```python
chunk.text == source_file.body[chunk.character_start : chunk.character_end]
```

Every chunk retains its source file ID, title, URL, publication date, domain,
language, and complete filterable metadata so later retrieval can filter and
cite chunks without a join.

## MongoDB Atlas persistence

MongoDB is optional during local generation and tests. Set `MONGODB_URI`,
`MONGODB_DATABASE`, `MONGODB_SOURCE_FILES_COLLECTION`, and
`MONGODB_CHUNKS_COLLECTION` only in the ignored `.env` file; `.env.example`
lists the required keys without a real credential. `MongoCorpusRepository`
accepts a database object and provides idempotent `upsert_source_files()` and
`upsert_chunks()` operations, keyed by `file_id` and `chunk_id`. Stored records
include `content_sha256` and an `ingestion_version` to make data provenance
explicit.

Reviewable MongoDB index definitions are in `infra/mongodb/`. The standard
geospatial indexes use `metadata.geo` in GeoJSON form, with coordinates always
ordered as `[longitude, latitude]`. The Atlas Search definition indexes chunk
text and titles while mapping the planned filter fields. The checked-in vector
definition uses the selected Gemini 768-dimensional embedding contract.

`docker compose up --build` also starts a MongoDB 7 container for local
integration work. The API receives its service-local connection string from
Compose, and MongoDB data is retained in the named `mongo_data` volume. Stop
the stack with `docker compose down`; use `docker compose down -v` only when
you deliberately want to remove local database data.

To run the live persistence check against that local service, start MongoDB and
provide its URI explicitly:

```bash
docker compose up -d --wait mongo
MONGODB_URI=mongodb://127.0.0.1:27017 python -m pytest -m integration
docker compose down
```

The integration test writes only to `agent_search_integration_test` and removes
that database after the assertion run.

## Lexical search API

`POST /v1/search` provides a deterministic, dependency-free BM25 baseline over
the generated chunks. It accepts a versioned request with `query`, optional
filters, and a result limit. Filters cover domain, language, region, tag,
category, publication-date range, and a geographic radius for location records.

Every result is grounded evidence rather than an untraceable answer: it includes
the chunk and file IDs, rank and score, exact chunk text, body-relative character
offsets, source title and URL, publication date, and copied source metadata.
Invalid request shapes, empty queries, out-of-range coordinates, and reversed
date ranges return FastAPI validation errors.

```bash
curl -X POST http://127.0.0.1:8000/v1/search \
  -H 'content-type: application/json' \
  -d '{"query":"Busan cargo terminal weather","filters":{"region":"busan"}}'
```

The local retriever is intentionally separate from the Atlas Search adapter so
both can be tested and measured independently. The Atlas adapter expresses the
same text and metadata filtering shape, while this milestone remains runnable
without Atlas credentials.

To run the Atlas Search adapter smoke test locally, start the separate
Search-enabled MongoDB profile. It provisions the checked-in search index,
loads generated chunks, and executes the adapter's real `$search` pipeline:

```bash
docker compose --profile search up -d --wait mongo-search
ATLAS_LOCAL_URI='mongodb://127.0.0.1:27018/?directConnection=true' \
  python -m pytest -m atlas_local
docker compose --profile search down
```

The `mongo-search` container uses `mongodb/mongodb-atlas-local` for local
development and CI only; it is not a production Atlas deployment.

### End-to-end grounded result

```json
{
  "query": "Busan cargo terminal weather",
  "ranking_version": "lexical-bm25-v1",
  "degraded": false,
  "results": [{
    "chunk_id": "news-busan-port-weather-delay-chunk-000",
    "source_url": "https://example.invalid/news/busan-port-weather-delay",
    "character_start": 0,
    "character_end": 1022,
    "text": "...",
    "metadata": {"region": "busan", "tags": ["cargo", "weather"]}
  }]
}
```

An agent can cite the returned source URL and inspect the exact body-relative
chunk range; it never needs to trust an unsupported generated answer.

## Semantic and hybrid retrieval

The selected semantic contract is Gemini `gemini-embedding-2`, requested at 768
dimensions and L2 normalized. The model name, dimensions, normalization,
embedding version, and content checksum are stored with each vector. This lets
the embedding command resume safely: it only sends chunks with absent vectors,
a changed chunk checksum, or a changed embedding contract.

Copy `.env.example` to the ignored `.env` file, then set `GEMINI_API_KEY` to a
Gemini Developer API key. Keep the remaining embedding values aligned as a
single contract: `EMBEDDING_MODEL=gemini-embedding-2`,
`EMBEDDING_DIMENSIONS=768`, `EMBEDDING_VERSION=gemini-embedding-2-768-l2-v1`,
and `EMBEDDING_NORMALIZATION=l2`. Never place the API key in `.env.example` or
commit `.env`.

Generate a separate, uncommitted vector artifact:

```bash
python -m agent_search.corpus.embeddings
```

The command reads `data/derived/chunks.jsonl` and writes
`data/derived/chunks.embedded.jsonl`; raw inputs and the baseline generated
fixture remain unchanged. The checked-in Atlas Vector Search definition is
`infra/mongodb/chunks.vector-search-index.json`. Local BM25 and vector retrieval
remain independent, and `HybridRetriever` combines their candidate lists with
deterministic reciprocal-rank fusion (RRF, default `k=60`).

### Semantic-hybrid demo

Run a credential-free demonstration of BM25 plus vector ranking fused with RRF:

```bash
python examples/hybrid_retrieval_demo.py "Busan cargo terminal weather delay"
```

It prints ranked, grounded chunk IDs, source titles, and source URLs. The demo
uses the deterministic hash embedder so it is reproducible without an API key;
the production embedding workflow above uses Gemini.

## Evaluation

`data/derived/chunk-qrels.jsonl` contains graded chunk-level relevance labels
derived from the reviewed fictional corpus. The evaluation harness calculates
Recall@k, MRR@k, and nDCG@k for lexical, vector, and RRF retrieval. The current
Gemini-backed synthetic benchmark is recorded in
[`docs/benchmark-report.md`](docs/benchmark-report.md); it is a reproducible
contract check, not a production-performance claim.

## Observability

Every search response identifies its `ranking_version` and whether retrieval was
degraded. Search logs use a caller-supplied `X-Correlation-ID` (or generated
UUID), a query hash rather than raw query text, applied filters, result count,
and retrieval latency. `GET /metrics` exposes Prometheus-style request, result,
and cache-hit counters for local monitoring.

## Retrieval tradeoffs

Files remain canonical provenance records; chunks are the retrieval units, so a
chunk can be ranked and cited without losing its originating file. Filterable
metadata is copied to chunks to make filtering a single-index operation. BM25
is fast and transparent for exact terms; vectors help semantic matches; RRF
combines both rankings without forcing their raw scores onto the same scale.
Introduce a reranker only when benchmark errors show its extra latency is worth
the tradeoff.

## License

MIT
