from django.utils.timezone import now
from django.core.cache import cache
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Article
from .serializers import PublicArticleDetailSerializer
from .cache import get_articles_cache_version


class PublicArticle(APIView):
    """
    PUBLIC
    GET /api/articles/<section>/<slug>/?lang=te
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section, slug):
        lang = request.GET.get("lang", "te").strip()

        # Check cache first with versioning
        ver = get_articles_cache_version()
        cache_key = f"v{ver}:article_detail:{section}:{slug}:{lang}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached), status=status.HTTP_200_OK)

        article = (
            Article.objects
            .filter(section=section, slug=slug)
            .prefetch_related(
                'media_links__media', 
                'translations',
                'article_categories__category',
                'article_categories__category__section',
                'article_categories__category__parent'
            )
            .first()
        )
        if not article:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if article.status not in ["PUBLISHED", "SCHEDULED"]:
            return Response({"error": "Not available"}, status=status.HTTP_410_GONE)

        if article.published_at and article.published_at > now():
            return Response({"error": "Scheduled"}, status=status.HTTP_404_NOT_FOUND)

        if article.expires_at and article.expires_at < now():
            return Response({"error": "Expired"}, status=status.HTTP_410_GONE)

        # Strict language matching: Ensure translation exists for specifically requested lang
        translation_exists = article.translations.filter(language=lang).exists()
        if not translation_exists:
             return Response({"error": f"Content not available in {lang}"}, status=status.HTTP_404_NOT_FOUND)

        serializer = PublicArticleDetailSerializer(
            article, 
            context={"lang": lang, "request": request}
        )

        # Cache for 5 minutes (300 seconds) with versioning
        cache.set(cache_key, json.dumps(serializer.data, default=str), timeout=300)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
