import json
from django.core.cache import cache
from django.utils.timezone import now
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Article, ArticleCategory
from .cache import get_articles_cache_version
from .pagination import PublicArticlesPagination
from apps.taxonomy.models import Category


class PublishedArticlesList(APIView):
    """
    PUBLIC
    GET /api/articles/published/?section=academics&category=intermediate&limit=10&cursor=<cursor>
    
    Filters:
    - section: Filter by article section (e.g., 'academics', 'exams', 'news')
    - category: Filter by category slug. Can be hierarchical (e.g., 'intermediate' under 'academics' section)
    
    Returns published articles with cursor-based pagination.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        section = request.GET.get("section")
        category_slug = request.GET.get("category")
        cursor = request.GET.get("cursor")

        # Build cache key
        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:published:{section}:{category_slug}:{cursor}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # Base queryset: only published, visible, non-expired articles
        qs = Article.objects.prefetch_related(
            'translations', 
            'article_categories__category',
            'media_links__media'
        ).filter(
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now()
        )
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        # Filter by section
        if section:
            qs = qs.filter(Q(section__iexact=section) | Q(article_sections__section__iexact=section)).distinct()

        # Filter by category (hierarchical support)
        if category_slug:
            # Find the category by slug within the section (if provided)
            category_filter = Q(slug=category_slug)
            if section:
                category_filter &= Q(section__slug__iexact=section)
            
            try:
                category = Category.objects.filter(category_filter).first()
                if category:
                    # Get all child categories recursively
                    category_ids = self._get_category_tree_ids(category)
                    # Filter articles that have any of these categories
                    qs = qs.filter(article_categories__category_id__in=category_ids).distinct()
            except Category.DoesNotExist:
                # If category doesn't exist, return empty results
                return Response({
                    "results": [],
                    "next_cursor": None,
                    "has_next": False,
                    "limit": PublicArticlesPagination.page_size
                }, status=200)

        # Apply pagination
        paginator = PublicArticlesPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            lang = request.GET.get("lang", "te").strip()
            from .utils import prepare_article_card
            results = [x for x in [prepare_article_card(a, lang) for a in page] if x]

            response = paginator.get_paginated_response(results)
            cache.set(cache_key, json.dumps(response.data, default=str), timeout=300)
            return response

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)

    def _get_category_tree_ids(self, category):
        """
        Recursively get all category IDs including the parent and all children.
        """
        ids = [category.id]
        children = Category.objects.filter(parent=category)
        for child in children:
            ids.extend(self._get_category_tree_ids(child))
        return ids

class RelatedArticlesView(APIView):
    """
    PUBLIC
    GET /api/articles/<section>/<slug>/related/?lang=te
    
    Returns articles sharing categories or tags with the source article.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, section, slug):
        lang = request.GET.get("lang", "te").strip()

        # Check cache
        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:related:{section}:{slug}:{lang}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # 1. Get source article
        source = Article.objects.filter(section=section, slug=slug).first()
        if not source:
            return Response({"results": []})

        # 2. Get categories and tags
        category_ids = list(source.article_categories.values_list('category_id', flat=True))
        tags = source.tags or []

        # 3. Build related articles query
        # Must be PUBLISHED, non-expired, and NOT the source article
        qs = Article.objects.prefetch_related(
            'translations', 
            'article_categories__category',
            'media_links__media'
        ).filter(
            status="PUBLISHED",
            noindex=False,
            published_at__lte=now()
        ).exclude(id=source.id)
        
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        # Match by category OR tags
        match_q = Q()
        if category_ids:
            match_q |= Q(article_categories__category_id__in=category_ids)
        
        if tags:
            # Match if any of the source tags are present in the target tags list
            tag_q = Q()
            for tag in tags:
                tag_q |= Q(tags__contains=tag)
            match_q |= tag_q

        if not category_ids and not tags:
             # Fallback: latest in same section
             qs = qs.filter(section=section)
        else:
             qs = qs.filter(match_q).distinct()

        # 4. Final ordering and limit
        qs = qs.order_by("-published_at")[:5]

        from .utils import prepare_article_card
        results = [x for x in [prepare_article_card(a, lang) for a in qs] if x]

        data = {"results": results}
        cache.set(cache_key, json.dumps(data, default=str), timeout=300)
        return Response(data)

class TopStoriesView(APIView):
    """
    PUBLIC
    GET /api/articles/top-stories/?lang=te
    
    Returns the latest 5 top stories (is_top_story=True),
    excluding expired ones.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        limit = 5
        lang = request.GET.get("lang", "te").strip()

        # Build cache key
        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:top_stories:{lang}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # Base queryset: is_top_story=True, PUBLISHED, non-expired
        qs = Article.objects.prefetch_related(
            'translations', 
            'article_categories__category',
            'media_links__media'
        ).filter(
            is_top_story=True,
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now()
        )
        # Expiry filter
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        # Order by latest published
        qs = qs.order_by("-published_at")[:limit]

        from .utils import prepare_article_card
        results = [x for x in [prepare_article_card(a, lang) for a in qs] if x]

        data = {"results": results}
        cache.set(cache_key, json.dumps(data, default=str), timeout=300)
        return Response(data)
