# Raw source files

These Markdown files are the immutable inputs for the retrieval pipeline. They
are deliberately fictional, but they resemble the two target source domains:

- `news/`: news articles with a publication date, region, topic tags, and body.
- `locations/`: place profiles with coordinates, category, operating details,
  and descriptive body text.

Each file uses TOML front matter. The ingestion step creates a file-level record
from this source metadata and content, including a checksum and source path.
Later partitioning creates chunks that retain the file ID and filterable
metadata; it must not overwrite or discard the raw file. Location files use
`coordinates = [longitude, latitude]`, which becomes a GeoJSON `Point` in the
derived record.

The `synthetic.example` URLs and every claim in these files are fictional. No
real articles, places, users, or proprietary source content is included.
