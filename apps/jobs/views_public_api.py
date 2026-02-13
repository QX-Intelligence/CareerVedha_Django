from django.utils.timezone import now
from django.db.models import F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Job, JobViewEvent


class PublicJobDetailAPI(APIView):
    """
    PUBLIC
    GET /api/jobs/<slug>/
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, slug):
        job = Job.objects.filter(slug=slug).first()

        if not job:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        if not job.status:  # status 0 = inactive
            return Response({"error": "Job not available"}, status=status.HTTP_410_GONE)

        if job.application_end_date and job.application_end_date < now().date():
            return Response({"error": "Job expired"}, status=status.HTTP_410_GONE)

        # ✅ Track view event
        JobViewEvent.objects.create(
            job=job,
            ip=self._get_client_ip(request),
            user_agent=(request.headers.get("User-Agent") or "")[:500],
        )

        # ✅ Increment view counter (FAST)
        Job.objects.filter(id=job.id).update(views_count=F("views_count") + 1)
        job.refresh_from_db(fields=["views_count"])

        return Response(
            {
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
            },
            status=status.HTTP_200_OK,
        )

    def _get_client_ip(self, request):
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
