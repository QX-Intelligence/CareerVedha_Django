from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.cache import cache
import json

from .models import Article
from .cache import get_articles_cache_version
from .pagination import TrendingArticlesPagination
from .utils import prepare_article_card


class TrendingArticles(APIView):
    """
    PUBLIC
    GET /api/articles/trending/?section=academics&limit=20&lang=te
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        lang = request.GET.get("lang", "te")
        section = request.GET.get("section")

        ver = get_articles_cache_version()
        cursor = request.GET.get("cursor")
        cache_key = f"v{ver}:articles:trending:{section}:{lang}:{cursor}"
        
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached), status=200)

        qs = Article.objects.filter(
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now()
        ).prefetch_related('translations', 'media_links__media', 'article_categories__category')
        
        if section:
            qs = qs.filter(section=section)

        qs = qs.exclude(expires_at__isnull=False, expires_at__lt=now())
        
        paginator = TrendingArticlesPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            results = []
            for a in page:
                card = prepare_article_card(a, lang)
                if card:
                    results.append(card)
            
            response = paginator.get_paginated_response(results)
            cache.set(cache_key, json.dumps(response.data, default=str), timeout=300)
            return response

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)
