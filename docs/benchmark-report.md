# Synthetic retrieval benchmark

These measurements use only the repository's fictional corpus; they are not
production performance claims. Gemini `gemini-embedding-2` generated the vector
and RRF inputs at 768 dimensions. Values are the mean across six labeled queries
and nine chunks; latency measures local retrieval only, excluding the one-time
embedding generation call.

| Configuration | Recall@5 | MRR@5 | nDCG@5 | Mean retrieval latency (ms) |
| --- | ---: | ---: | ---: | ---: |
| lexical | 0.917 | 1.000 | 0.870 | 0.315 |
| vector | 1.000 | 1.000 | 0.947 | 2.662 |
| rrf | 1.000 | 1.000 | 0.918 | 2.246 |

The sample is deliberately tiny and synthetic. It demonstrates a reproducible
evaluation contract, rather than a statistically meaningful comparison of
production retrieval configurations.
