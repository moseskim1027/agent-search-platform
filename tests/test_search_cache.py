import pytest

from agent_search.app.cache import TTLCache


def test_cache_expires_entries_at_the_configured_ttl() -> None:
    now = [100.0]
    cache = TTLCache[str](ttl_seconds=5, max_entries=2, clock=lambda: now[0])
    cache.put("query", "evidence")

    now[0] = 104.9
    assert cache.get("query") == "evidence"
    now[0] = 105.0
    assert cache.get("query") is None


def test_cache_evicts_the_least_recently_used_entry() -> None:
    cache = TTLCache[str](ttl_seconds=60, max_entries=2)
    cache.put("first", "a")
    cache.put("second", "b")
    assert cache.get("first") == "a"

    cache.put("third", "c")

    assert cache.get("first") == "a"
    assert cache.get("second") is None
    assert cache.get("third") == "c"


@pytest.mark.parametrize("ttl,capacity", [(0, 1), (1, 0)])
def test_cache_rejects_invalid_limits(ttl: int, capacity: int) -> None:
    with pytest.raises(ValueError):
        TTLCache[str](ttl_seconds=ttl, max_entries=capacity)
