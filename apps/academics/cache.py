from django.core.cache import cache

ACADEMICS_CACHE_VER_KEY = "academics:version"

def get_academics_cache_version() -> int:
    ver = cache.get(ACADEMICS_CACHE_VER_KEY)
    if ver is None:
        cache.set(ACADEMICS_CACHE_VER_KEY, 1, None)
        return 1
    try:
        return int(ver)
    except (ValueError, TypeError):
        cache.set(ACADEMICS_CACHE_VER_KEY, 1, None)
        return 1

def bump_academics_cache() -> None:
    try:
        cache.incr(ACADEMICS_CACHE_VER_KEY)
    except Exception:
        ver = get_academics_cache_version()
        cache.set(ACADEMICS_CACHE_VER_KEY, ver + 1, None)