import json
from django.utils.timezone import now
from django.core.cache import cache
from django.utils.dateparse import parse_datetime
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Job
from .cache import get_jobs_cache_version


from .pagination import JobsCursorPagination


class PublicJobList(APIView):
    """
    GET /api/jobs/?job_type=GOVT&location=AP&limit=10&cursor=<cursor>

    Standardized to use JobsCursorPagination.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        job_type = request.GET.get("job_type")
        location = request.GET.get("location")

        # -------------------------
        # Cache key (cursor handled by DRF)
        # -------------------------
        ver = get_jobs_cache_version()
        cursor = request.GET.get("cursor")
        cache_key = f"v{ver}:jobs:list:{job_type}:{location}:{cursor}"

        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # -------------------------
        # Base queryset
        # -------------------------
        qs = (
            Job.objects.filter(
                status=1,  # Active jobs only
                application_end_date__gte=now().date(),
            )
            .order_by("-created_at", "-id")
        )

        if job_type:
            qs = qs.filter(job_type=job_type)

        if location:
            qs = qs.filter(location__icontains=location)

        paginator = JobsCursorPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            results = [
                {
                    "id": j.id,
                    "title": j.title,
                    "slug": j.slug,
                    "job_type": j.job_type,
                    "organization": j.organization,
                    "department": j.department,
                    "location": j.location,
                    "qualification": j.qualification,
                    "experience": j.experience,
                    "vacancies": j.vacancies,
                    "application_end_date": j.application_end_date,
                    "salary": j.salary,
                    "apply_url": j.apply_url,
                    "status": j.status,
                    "views_count": j.views_count,
                    "created_at": j.created_at,
                }
                for j in page
            ]
            response = paginator.get_paginated_response(results)
            cache.set(cache_key, json.dumps(response.data, default=str), timeout=60)
            return response

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        })
