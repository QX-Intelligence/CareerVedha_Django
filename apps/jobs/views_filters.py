from django.utils.timezone import now
from django.db.models import Count

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Job


class PublicJobFilters(APIView):
    """
    PUBLIC
    GET /api/jobs/filters/
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        today = now().date()

        qs = Job.objects.filter(
            status=1,  # Active jobs only
            application_end_date__gte=today,
        )

        job_type_counts = (
            qs.values("job_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        top_locations = (
            qs.exclude(location="")
            .values("location")
            .annotate(count=Count("id"))
            .order_by("-count")[:20]
        )

        top_orgs = (
            qs.exclude(organization="")
            .values("organization")
            .annotate(count=Count("id"))
            .order_by("-count")[:20]
        )

        return Response(
            {
                "job_type_counts": list(job_type_counts),
                "top_locations": list(top_locations),
                "top_organizations": list(top_orgs),
            },
            status=status.HTTP_200_OK,
        )
