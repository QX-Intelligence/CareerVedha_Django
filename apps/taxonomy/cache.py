from django.core.cache import cache

TAXONOMY_VERSION_KEY = "taxonomy_cache_version"
TAXONOMY_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

def get_taxonomy_version():
    """Gets the current cache version for taxonomy APIs."""
    version = cache.get(TAXONOMY_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(TAXONOMY_VERSION_KEY, version, timeout=None)
    return version

def clear_taxonomy_cache():
    """
    Invalidates all taxonomy caches by bumping the global taxonomy version.
    This guarantees fresh reads across all taxonomy endpoints immediately.
    """
    try:
        cache.incr(TAXONOMY_VERSION_KEY)
    except ValueError:
        # If key doesn't exist, set it
        cache.set(TAXONOMY_VERSION_KEY, 1, timeout=None)

def get_taxonomy_cache_key(prefix, *args, **kwargs):
    """
    Generates a versioned cache key for taxonomy endpoints.
    Example: taxonomy_v2_TaxonomyTree_section:academics
    """
    version = get_taxonomy_version()
    
    parts = [str(prefix)]
    if args:
        parts.extend(str(a) for a in args)
    if kwargs:
        # Sort kwargs to ensure consistent keys regardless of dict order
        parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()) if v is not None)
        
    # Replace spaces or problematic characters if needed, though usually standard slugs/int are safe
    base_key = "_".join(parts).replace(" ", "_").replace("/", "_")
    
    return f"taxonomy_v{version}_{base_key}"
