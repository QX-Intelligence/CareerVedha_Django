from django.db.models import F
from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Article
from .cache import bump_articles_cache_version


class TrackArticleView(APIView):
    """
    PUBLIC
    POST /api/articles/<section>/<slug>/track-view/
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, section, slug):
        article = Article.objects.filter(
            section=section,
            slug=slug,
            status="PUBLISHED",
            noindex=False,
        ).first()

        if not article:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        Article.objects.filter(id=article.id).update(
            views_count=F("views_count") + 1,
            last_viewed_at=now()
        )

        bump_articles_cache_version()
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
