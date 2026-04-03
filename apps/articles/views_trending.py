from django.utils.timezone import now
from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
import json

from .models import Article, ArticleTranslation
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
        lang = request.GET.get("lang", "te").strip().lower()
        section = request.GET.get("section")
        cursor = request.GET.get("cursor")
        limit = request.GET.get("limit", 20)

        # --- CACHE DISABLED FOR TESTING ---
        # ver = get_articles_cache_version()
        # cache_key = f"v{ver}:articles:trending:{section}:{lang}:{limit}:{cursor}"
        # cached = cache.get(cache_key)
        # if cached:
        #     return Response(json.loads(cached), status=200)

        qs = Article.objects.filter(
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now(),
            translations__language__iexact=lang
        ).prefetch_related(
            Prefetch(
                'translations',
                queryset=ArticleTranslation.objects.filter(language__iexact=lang)
            ),
            'media_links__media',
            'article_categories__category'
        ).distinct().order_by("-views_count", "-published_at", "-id")
        
        if section:
            qs = qs.filter(section=section)

        qs = qs.exclude(expires_at__isnull=False, expires_at__lt=now())
        
        paginator = TrendingArticlesPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            results = []
            for a in page:
                card = prepare_article_card(a, lang, strict=True)
                if card:
                    results.append(card)
            
            response = paginator.get_paginated_response(results)
            # --- CACHE DISABLED FOR TESTING ---
            # cache.set(cache_key, json.dumps(response.data, default=str), timeout=300)
            return response

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)
