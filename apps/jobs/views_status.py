from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.common.jwt import get_user_from_jwt
from apps.common.permissions import require_min_role

from .models import Job
from .cache import bump_jobs_cache_version


class ActivateJob(APIView):
    """
    PATCH /api/cms/jobs/<job_id>/activate/
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

        return Response({"status": "ACTIVE"}, status=status.HTTP_200_OK)


class DeactivateJob(APIView):
    """
    PATCH /api/cms/jobs/<job_id>/deactivate/
    Role: PUBLISHER+
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

    def patch(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        job.status = 0  # Inactive
        job.save(update_fields=["status"])

        bump_jobs_cache_version()

        return Response({"status": "INACTIVE"}, status=status.HTTP_200_OK)
