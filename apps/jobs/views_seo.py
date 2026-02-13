from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os

from .models import Job

SITE_DOMAIN = os.getenv("SITE_DOMAIN", "localhost:8000")


class JobSEO(APIView):
    """
    PUBLIC
    GET /api/jobs/<slug>/seo/
    Returns meta + schema json-ld
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

        canonical_url = f"https://{SITE_DOMAIN}/jobs/{job.slug}/"

        title = f"{job.title} | Career Vedha Jobs"
        description = f"Apply for {job.title} at {job.organization}. Location: {job.location}. Last date: {job.application_end_date}."

        schema = {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": job.title,
            "description": job.job_description[:1500],
            "datePosted": job.created_at.date().isoformat(),
            "validThrough": job.application_end_date.isoformat(),
            "employmentType": "FULL_TIME" if job.job_type == "PRIVATE" else "OTHER",
            "hiringOrganization": {
                "@type": "Organization",
                "name": job.organization or "Career Vedha",
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": job.location or "India",
                    "addressCountry": "IN",
                },
            },
            "applicantLocationRequirements": {
                "@type": "Country",
                "name": "India",
            },
            "url": canonical_url,
        }

        return Response(
            {
                "title": title,
                "description": description,
                "canonical": canonical_url,
                "robots": "index,follow",
                "schema": schema,
            },
            status=status.HTTP_200_OK,
        )
