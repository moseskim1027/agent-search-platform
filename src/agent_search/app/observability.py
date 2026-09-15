"""Minimal dependency-free request telemetry for the local API."""

import hashlib
import json
import logging
from collections import Counter
from threading import Lock

logger = logging.getLogger("agent_search.request")


class SearchMetrics:
    """Thread-safe Prometheus text metrics for search request outcomes."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.requests: Counter[str] = Counter()
        self.results = 0
        self.cache_hits = 0

    def record(self, *, status: str, result_count: int, cache_hit: bool) -> None:
        with self._lock:
            self.requests[status] += 1
            self.results += result_count
            self.cache_hits += int(cache_hit)

    def render(self) -> str:
        with self._lock:
            lines = ["# TYPE agent_search_requests_total counter"]
            lines.extend(
                f'agent_search_requests_total{{status="{status}"}} {count}'
                for status, count in sorted(self.requests.items())
            )
            lines.extend(
                [
                    "# TYPE agent_search_results_total counter",
                    f"agent_search_results_total {self.results}",
                    "# TYPE agent_search_cache_hits_total counter",
                    f"agent_search_cache_hits_total {self.cache_hits}",
                ]
            )
            return "\n".join(lines) + "\n"


def query_hash(query: str) -> str:
    """Return a non-reversible short query identifier for logs."""

    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def log_search(**fields: object) -> None:
    """Emit one structured event without recording raw query text."""

    logger.info(json.dumps(fields, sort_keys=True))
