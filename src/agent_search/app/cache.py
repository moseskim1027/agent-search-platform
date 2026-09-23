"""Small bounded TTL cache for safe reuse of search responses."""

from collections import OrderedDict
from collections.abc import Callable
from threading import Lock
from time import monotonic
from typing import Generic, TypeVar

Value = TypeVar("Value")


class TTLCache(Generic[Value]):
    """Thread-safe LRU cache that never serves entries past their TTL."""

    def __init__(
        self, *, ttl_seconds: float, max_entries: int, clock: Callable[[], float] = monotonic
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.clock = clock
        self._entries: OrderedDict[str, tuple[float, Value]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Value | None:
        """Return an unexpired value and mark it as recently used."""

        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            created_at, value = entry
            if self.clock() - created_at >= self.ttl_seconds:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return value

    def put(self, key: str, value: Value) -> None:
        """Store a value, evicting the least-recently used entry when full."""

        with self._lock:
            self._entries[key] = (self.clock(), value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
