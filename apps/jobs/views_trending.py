from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
import json

from .models import Job
from .cache import get_jobs_cache_version
from .pagination import TrendingJobsPagination

class TrendingJobs(APIView):
    """
    PUBLIC
    GET /api/jobs/trending/
    List trending jobs by views count
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        today = now().date()
        ver = get_jobs_cache_version()
        cursor = request.GET.get("cursor")
        cache_key = f"v{ver}:jobs:trending:{cursor}"
        
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached), status=status.HTTP_200_OK)

        qs = Job.objects.filter(
            status=1,  # Active jobs only
            application_end_date__gte=today,
        )

        paginator = TrendingJobsPagination()
        page = paginator.paginate_queryset(qs, request)

        results = [
            {
                "id": job.id,
                "title": job.title,
                "slug": job.slug,
                "job_type": job.job_type,
                "organization": job.organization,
                "location": job.location,
                "application_end_date": job.application_end_date,
                "status": job.status,
                "views_count": job.views_count,
                "created_at": job.created_at,
            }
            for job in page
        ]
        
        response = paginator.get_paginated_response(results)
        cache.set(cache_key, json.dumps(response.data, default=str), timeout=60)
        return response
