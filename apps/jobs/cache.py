from django.core.cache import cache

JOBS_CACHE_VER_KEY = "jobs:ver"


def get_jobs_cache_version() -> int:
    ver = cache.get(JOBS_CACHE_VER_KEY)
    if ver is None:
        cache.set(JOBS_CACHE_VER_KEY, 1, None)
        return 1
    try:
        return int(ver)
    except Exception:
        cache.set(JOBS_CACHE_VER_KEY, 1, None)
        return 1


def bump_jobs_cache_version() -> None:
    try:
        cache.incr(JOBS_CACHE_VER_KEY)
    except Exception:
        ver = get_jobs_cache_version()
        cache.set(JOBS_CACHE_VER_KEY, ver + 1, None)
