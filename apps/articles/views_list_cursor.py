import json
from django.core.cache import cache
from django.utils.timezone import now
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Article
from .cache import get_articles_cache_version
from .pagination import PublicArticlesPagination


class PublicArticlesListCursor(APIView):
    """
    PUBLIC
    GET /api/articles/list/?section=academics&limit=10&cursor=<id>
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        section = request.GET.get("section")
        cursor = request.GET.get("cursor")

        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:list:{section}:{cursor}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        qs = Article.objects.filter(status="PUBLISHED", noindex=False, published_at__lte=now())
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        if section:
            qs = qs.filter(section=section)

        paginator = PublicArticlesPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            results = [
                {
                    "id": a.id,
                    "slug": a.slug,
                    "section": a.section,
                    "summary": a.summary,
                    "published_at": a.published_at,
                    "created_at": a.created_at,
                }
                for a in page
            ]

            response = paginator.get_paginated_response(results)
            cache.set(cache_key, json.dumps(response.data, default=str), timeout=300)
            return response

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)
