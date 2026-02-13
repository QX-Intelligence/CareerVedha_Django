from django.utils.timezone import now
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.core.cache import cache
import json

from .models import Job
from .cache import get_jobs_cache_version


class JobSearchSuggestions(APIView):
    """
    PUBLIC
    GET /api/jobs/search-suggestions/?q=assis
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        if not q or len(q) < 2:
            return Response({"suggestions": []}, status=status.HTTP_200_OK)

        today = now().date()

        ver = get_jobs_cache_version()
        cache_key = f"v{ver}:jobs:suggest:{q.lower()}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached), status=status.HTTP_200_OK)

        qs = Job.objects.filter(
            status=1,  # Active jobs only
            application_end_date__gte=today,
        ).filter(
            Q(title__icontains=q)
            | Q(organization__icontains=q)
            | Q(location__icontains=q)
        ).order_by("-views_count", "-id")[:10]

        data = {
            "suggestions": [
                {
                    "title": job.title,
                    "slug": job.slug,
                    "organization": job.organization,
                    "location": job.location,
                }
                for job in qs
            ]
        }

        cache.set(cache_key, json.dumps(data, default=str), timeout=60)
        return Response(data, status=status.HTTP_200_OK)
