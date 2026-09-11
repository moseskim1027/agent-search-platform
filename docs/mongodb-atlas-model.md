# MongoDB Atlas data model

The raw Markdown files remain the canonical, vendor-neutral inputs. Ingestion
creates one `SourceFile` record per file; future partitioning will create one
`ChunkRecord` per chunk. These records are shaped for MongoDB Atlas without
requiring a database connection during local development.

```text
raw file -> source_files collection -> chunks collection -> Atlas Search / Vector Search
```

`source_files` preserves the entire raw text, content checksum, source path,
source URL, and parsed metadata. `chunks` will duplicate only the metadata
needed for filtering and grounding: `domain`, `language`, `published_at`,
`metadata.region`, `metadata.tags`, `metadata.category`, and `metadata.geo`.

Location coordinates use GeoJSON `Point` form with `[longitude, latitude]`.
This allows a future Atlas geospatial index and prevents coordinate-order bugs.
The `embedding` field is intentionally nullable until a model and vector
dimension are selected.

Recommended future indexes:

- Atlas Search text index on `text`, `source_title`, and metadata fields used
  for filtering.
- Atlas Vector Search index on `embedding` once its dimension is fixed.
- Geospatial index on `metadata.geo` for location-radius and containment filters.

The relevant model contracts live in `src/agent_search/corpus/schemas.py`.

