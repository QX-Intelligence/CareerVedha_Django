import json
from django.core.cache import cache
from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.taxonomy.models import Category
from .models import Article, ArticleCategory
from .cache import get_articles_cache_version
from .utils import prepare_article_card


class CategoryBlockArticles(APIView):
    """
    PUBLIC
    GET /api/articles/category-block/?section=academics&lang=te&limit=6
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        section = (request.GET.get("section") or "").strip()
        lang = (request.GET.get("lang") or "te").strip()
        limit = int(request.GET.get("limit", 6))
        limit = max(1, min(limit, 20))

        if not section:
            return Response({"error": "section is required"}, status=status.HTTP_400_BAD_REQUEST)

        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:category_blocks:{section}:{lang}:{limit}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached), status=200)

        today = now()

        root_categories = Category.objects.filter(
            section=section,
            parent__isnull=True,
            is_active=True
        ).order_by("name")

        blocks = []

        for cat in root_categories:
            article_ids = (
                ArticleCategory.objects.filter(category=cat)
                .values_list("article_id", flat=True)
            )

            qs = (
                Article.objects.filter(
                    id__in=article_ids,
                    status="PUBLISHED",
                    noindex=False,
                    published_at__lte=today
                )
                .prefetch_related('translations', 'media_links__media', 'article_categories__category')
                .exclude(expires_at__isnull=False, expires_at__lt=today)
                .order_by("-published_at", "-id")[:limit]
            )

            results = []
            for a in qs:
                card = prepare_article_card(a, lang)
                if card:
                    results.append(card)

            blocks.append({
                "category": {
                    "id": cat.id,
                    "name": cat.name,
                    "slug": cat.slug,
                },
                "articles": results
            })

        cache.set(cache_key, json.dumps(blocks, default=str), timeout=300)

        return Response(blocks, status=status.HTTP_200_OK)
