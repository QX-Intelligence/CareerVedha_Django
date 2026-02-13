from django.core.cache import cache

ARTICLES_CACHE_VER_KEY = "articles:ver"


def get_articles_cache_version() -> int:
    ver = cache.get(ARTICLES_CACHE_VER_KEY)
    if ver is None:
        cache.set(ARTICLES_CACHE_VER_KEY, 1, None)
        return 1
    try:
        return int(ver)
    except Exception:
        cache.set(ARTICLES_CACHE_VER_KEY, 1, None)
        return 1


def bump_articles_cache_version() -> None:
    try:
        cache.incr(ARTICLES_CACHE_VER_KEY)
    except Exception:
        ver = get_articles_cache_version()
        cache.set(ARTICLES_CACHE_VER_KEY, ver + 1, None)
