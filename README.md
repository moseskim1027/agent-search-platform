# Agent Search Platform

A production-oriented reference project for grounded, multi-domain search APIs.
It will combine lexical retrieval, vector retrieval, rank fusion, reranking, and
evidence-rich results that an AI agent can safely consume.

## Status

The foundation is in place. The current service exposes health and metadata
endpoints; retrieval, indexing, evaluation, and observability will arrive in
separate, reviewable pull requests.

## Goals

- Search across news and financial-document domains.
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
2. Synthetic corpus: deterministic generators, schemas, and relevance labels.
3. Retrieval: BM25, vector search, and reciprocal-rank fusion.
4. Search contract: grounded results, filtering, and failure handling.
5. Evaluation and operations: benchmark suite, metrics, caching, and dashboards.

## Project layout

```text
src/agent_search/      Application package
tests/                 Automated tests
data/synthetic/        Generated synthetic fixtures (not committed yet)
docs/                  Architecture and decision records
```

## License

MIT
