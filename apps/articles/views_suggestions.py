from django.utils.timezone import now
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Article


class ArticleSearchSuggestions(APIView):
    """
    PUBLIC
    GET /api/articles/search-suggestions/?q=inter&section=academics&lang=te
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        lang = request.GET.get("lang", "te")
        section = request.GET.get("section")

        if not q or len(q) < 2:
            return Response({"suggestions": []}, status=status.HTTP_200_OK)

        qs = Article.objects.filter(status="PUBLISHED", noindex=False).exclude(
            expires_at__isnull=False,
            expires_at__lt=now()
        )

        if section:
            qs = qs.filter(section=section)

        qs = qs.filter(
            Q(translations__summary__icontains=q)
            | Q(translations__title__icontains=q)
        ).distinct().order_by("-views_count", "-id")[:10]

        suggestions = []
        for a in qs:
            tr = a.translations.filter(language=lang).first()
            display_title = tr.title if tr else a.title

            suggestions.append({
                "id": a.id,
                "slug": a.slug,
                "section": a.section,
                "title": display_title,
            })

        return Response({"suggestions": suggestions}, status=status.HTTP_200_OK)
