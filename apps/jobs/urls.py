from django.urls import path

from .views import CreateJob, UpdateJob, ListPublisherJobs, GetPublisherJob
from .views_publish import PublishJob, PublicJobDetail
from .views_status import ActivateJob, DeactivateJob

from .views_list_cursor import PublicJobList
from .views_public_api import PublicJobDetailAPI
from .views_filters import PublicJobFilters
from .views_suggestions import JobSearchSuggestions
from .views_trending import TrendingJobs
from .views_seo import JobSEO


urlpatterns = [
    # CMS - PUBLISHER+ ONLY
    path("api/django/cms/jobs/", CreateJob.as_view()),
    path("api/django/cms/jobs/list/", ListPublisherJobs.as_view()),
    path("api/django/cms/jobs/<int:job_id>/", UpdateJob.as_view()),
    path("api/django/cms/jobs/<int:job_id>/detail/", GetPublisherJob.as_view()),
    path("api/django/cms/jobs/<int:job_id>/activate/", ActivateJob.as_view()),
    path("api/django/cms/jobs/<int:job_id>/deactivate/", DeactivateJob.as_view()),

    # PUBLIC API
    path("api/django/jobs/", PublicJobList.as_view()),
    path("api/django/jobs/filters/", PublicJobFilters.as_view()),
    path("api/django/jobs/trending/", TrendingJobs.as_view()),
    path("api/django/jobs/search-suggestions/", JobSearchSuggestions.as_view()),
    path("api/django/jobs/<slug:slug>/seo/", JobSEO.as_view()),
    path("api/django/jobs/<slug:slug>/", PublicJobDetailAPI.as_view()),

    # Public website URL (later frontend)
    path("api/django/jobs/<slug:slug>/", PublicJobDetail.as_view()),
]
