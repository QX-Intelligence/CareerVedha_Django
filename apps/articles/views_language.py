import json
from django.core.cache import cache
from django.utils.timezone import now
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Article
from .cache import get_articles_cache_version
from .pagination import PublicArticlesPagination
from .utils import prepare_article_card


class LanguageFilteredArticles(APIView):
    """
    PUBLIC
    GET /api/articles/language/?lang=en&section=...&limit=20&cursor=...
    
    Filters articles that have a translation in the specified language.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        lang = request.GET.get("lang", "te").strip()
        section = request.GET.get("section")
        cursor = request.GET.get("cursor")

        # 1. Cache handling
        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:language:{lang}:{section}:{cursor}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached), status=status.HTTP_200_OK)

        # 2. Base Query: PUBLISHED, non-expired, and has requested language translation
        qs = Article.objects.prefetch_related(
            'translations',
            'article_categories__category',
            'media_links__media',
            'article_sections'
        ).filter(
            status="PUBLISHED",
            noindex=False,
            published_at__lte=now(),
            translations__language=lang  # 🌍 Crucial: Filter by translation language
        ).distinct()
        
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        # 3. Optional Section Filter
        if section:
            qs = qs.filter(Q(section=section) | Q(article_sections__section=section)).distinct()

        # 4. Pagination
        paginator = PublicArticlesPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            results = [x for x in [prepare_article_card(a, lang) for a in page] if x]
            
            response = paginator.get_paginated_response(results)
            # Cache for 5 minutes
            cache.set(cache_key, json.dumps(response.data, default=str), timeout=300)
            return response

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=status.HTTP_200_OK)