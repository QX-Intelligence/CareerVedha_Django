from django.utils.timezone import now
from django.db.models import Count

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import ArticleCategory, Article


class ArticleFilters(APIView):
    """
    PUBLIC
    GET /api/articles/filters/?section=academics
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        section = request.GET.get("section")

        qs = Article.objects.filter(status="PUBLISHED", noindex=False).exclude(
            expires_at__isnull=False,
            expires_at__lt=now()
        )

        if section:
            qs = qs.filter(section=section)

        total = qs.count()

        category_counts = (
            ArticleCategory.objects.filter(article__in=qs, category__is_active=True)
            .values("category_id")
            .annotate(count=Count("id"))
            .order_by("-count")[:25]
        )

        return Response(
            {
                "section": section or "",
                "total_published": total,
                "top_categories": list(category_counts),
            },
            status=status.HTTP_200_OK,
        )
