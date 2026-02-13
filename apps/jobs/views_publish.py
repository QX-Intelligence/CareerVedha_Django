from django.utils.timezone import now
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.common.jwt import get_user_from_jwt
from apps.common.permissions import require_min_role

from .models import Job
from .cache import bump_jobs_cache_version


class PublishJob(APIView):
    """
    PATCH /api/cms/jobs/<job_id>/publish/
    Role: PUBLISHER+
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

    def patch(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        job.status = 1  # Active
        job.save(update_fields=["status"])

        bump_jobs_cache_version()

        return Response({"status": "PUBLISHED"}, status=status.HTTP_200_OK)


class PublicJobDetail(APIView):
    """
    GET /jobs/<slug>/
    Public job page endpoint
    """

    def get(self, request, slug):
        job = Job.objects.filter(slug=slug).first()

        if not job:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        if not job.status:  # status 0 = inactive
            return Response({"error": "Job not available"}, status=status.HTTP_410_GONE)

        if job.application_end_date and job.application_end_date < now().date():
            return Response({"error": "Job expired"}, status=status.HTTP_410_GONE)

        return Response({
            "id": job.id,
            "title": job.title,
            "slug": job.slug,
            "job_type": job.job_type,
            "organization": job.organization,
            "department": job.department,
            "location": job.location,
            "qualification": job.qualification,
            "experience": job.experience,
            "vacancies": job.vacancies,
            "application_start_date": job.application_start_date,
            "application_end_date": job.application_end_date,
            "exam_date": job.exam_date,
            "job_description": job.job_description,
            "eligibility": job.eligibility,
            "selection_process": job.selection_process,
            "salary": job.salary,
            "apply_url": job.apply_url,
            "status": job.status,
            "status_display": "Active" if job.status == 1 else "Inactive",
            "views_count": job.views_count,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }, status=status.HTTP_200_OK)
