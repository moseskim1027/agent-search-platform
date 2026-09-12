# Agent Search Platform

A production-oriented reference project for grounded, multi-domain search APIs.
It will combine lexical retrieval, vector retrieval, rank fusion, reranking, and
evidence-rich results that an AI agent can safely consume.

## Status

The foundation is in place. The current service exposes health and metadata
endpoints; retrieval, indexing, evaluation, and observability will arrive in
separate, reviewable pull requests.

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

## Planned delivery sequence

1. Foundation: application structure, configuration, local developer workflow.
2. Raw corpus ingestion: file-level records, provenance, and relevance labels.
3. Partitioning: metadata-preserving chunks derived from source files.
4. Retrieval: BM25, vector search, and reciprocal-rank fusion.
5. Search contract: grounded results, filtering, and failure handling.
6. Evaluation and operations: benchmark suite, metrics, caching, and dashboards.

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
text and titles while mapping the planned filter fields. There is deliberately
no vector index yet because its required embedding dimension has not been
selected.

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

## License

MIT
