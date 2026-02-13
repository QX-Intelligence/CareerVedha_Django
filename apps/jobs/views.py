from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from apps.common.jwt import get_user_from_jwt
from apps.common.permissions import require_min_role
from .models import Job

from .cache import bump_jobs_cache_version

class CreateJob(APIView):
    """
    POST /api/cms/jobs/
    Role: PUBLISHER+
    Creates job and immediately publishes it (status=1)
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")
        request.cms_user = user

    def post(self, request):
        data = request.data
        user = request.cms_user

        # ✅ minimal validation
        required = ["title", "slug", "job_type", "application_end_date", "job_description"]
        for f in required:
            if f not in data or data[f] in [None, ""]:
                return Response({"error": f"{f} is required"}, status=400)

        job = Job.objects.create(
            title=data["title"],
            slug=data["slug"],
            job_type=data["job_type"],

            department=data.get("department", ""),
            organization=data.get("organization", ""),
            location=data.get("location", ""),

            qualification=data.get("qualification", ""),
            experience=data.get("experience", ""),
            vacancies=data.get("vacancies", 0),

            application_start_date=data.get("application_start_date") or None,
            application_end_date=data["application_end_date"],
            exam_date=data.get("exam_date") or None,

            job_description=data["job_description"],
            eligibility=data.get("eligibility", ""),
            selection_process=data.get("selection_process", ""),
            salary=data.get("salary", ""),

            apply_url=data.get("apply_url", ""),
            status=1,  # ✅ DIRECTLY PUBLISHED (1 = Active)
        )

        bump_jobs_cache_version()

        return Response(
            {"id": job.id, "status": "PUBLISHED", "message": "Job created and published successfully"},
            status=status.HTTP_201_CREATED
        )


class UpdateJob(APIView):
    """
    PATCH /api/cms/jobs/<job_id>/
    Role: PUBLISHER+
    Update job details (title, description, salary, etc.)
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

    def patch(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        data = request.data

        # ✅ Update only provided fields
        if "title" in data and data["title"]:
            job.title = data["title"]
        
        if "slug" in data and data["slug"]:
            job.slug = data["slug"]
        
        if "job_type" in data and data["job_type"]:
            job.job_type = data["job_type"]

        if "department" in data:
            job.department = data.get("department", "")
        
        if "organization" in data:
            job.organization = data.get("organization", "")
        
        if "location" in data:
            job.location = data.get("location", "")

        if "qualification" in data:
            job.qualification = data.get("qualification", "")
        
        if "experience" in data:
            job.experience = data.get("experience", "")
        
        if "vacancies" in data:
            try:
                job.vacancies = int(data["vacancies"])
            except (ValueError, TypeError):
                return Response({"error": "vacancies must be a number"}, status=400)

        if "application_start_date" in data:
            job.application_start_date = data.get("application_start_date") or None
        
        if "application_end_date" in data and data["application_end_date"]:
            job.application_end_date = data["application_end_date"]
        
        if "exam_date" in data:
            job.exam_date = data.get("exam_date") or None

        if "job_description" in data and data["job_description"]:
            job.job_description = data["job_description"]
        
        if "eligibility" in data:
            job.eligibility = data.get("eligibility", "")
        
        if "selection_process" in data:
            job.selection_process = data.get("selection_process", "")
        
        if "salary" in data:
            job.salary = data.get("salary", "")

        if "apply_url" in data:
            job.apply_url = data.get("apply_url", "")

        job.save()
        bump_jobs_cache_version()

        return Response(
            {
                "id": job.id,
                "status": "UPDATED",
                "message": "Job updated successfully"
            },
            status=status.HTTP_200_OK
        )


from .pagination import JobsCursorPagination

class ListPublisherJobs(APIView):
    """
    CMS
    GET /api/cms/jobs/list/
    Role: PUBLISHER+
    List all jobs for publisher (with filters)
    Query params:
    - status: 0 or 1 (filter by status)
    - job_type: GOVT or PRIVATE
    - search: search in title, organization, location
    - limit: default 20, max 100
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

    def get(self, request):
        # ✅ Get query parameters
        status_filter = request.GET.get("status")
        job_type = request.GET.get("job_type")
        search_query = request.GET.get("search", "").strip()
        
        # ✅ Base queryset
        qs = Job.objects.all().order_by("-created_at", "-id")

        # ✅ Filter by status
        if status_filter is not None:
            try:
                status_val = int(status_filter)
                if status_val in [0, 1]:
                    qs = qs.filter(status=status_val)
            except ValueError:
                return Response({"error": "status must be 0 or 1"}, status=400)

        # ✅ Filter by job_type
        if job_type:
            qs = qs.filter(job_type=job_type)

        # ✅ Search filter
        if search_query:
            qs = qs.filter(
                Q(title__icontains=search_query)
                | Q(organization__icontains=search_query)
                | Q(location__icontains=search_query)
            ).distinct()

        paginator = JobsCursorPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            results = [
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
                }
                for job in page
            ]
            
            return paginator.get_paginated_response(results)

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)


class GetPublisherJob(APIView):
    """
    GET /api/cms/jobs/<job_id>/detail/
    Role: PUBLISHER+
    Get specific job details
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)

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
            status=status.HTTP_200_OK
        )