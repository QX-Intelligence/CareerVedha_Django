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
            qs = qs.filter(section__iexact=section)

        # Filter by category (hierarchical support)
        if category_slug:
            # Find the category by slug within the section (if provided)
            category_filter = Q(slug=category_slug)
            if section:
                category_filter &= Q(section__iexact=section)
            
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
