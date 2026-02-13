from django.contrib import admin
from .models import Job, JobViewEvent


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "job_type",
        "organization",
        "location",
        "status",
        "application_end_date",
        "views_count",
        "created_at",
    )
    list_filter = ("job_type", "status", "location", "organization")
    search_fields = ("title", "slug", "organization", "location")


@admin.register(JobViewEvent)
class JobViewEventAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "ip", "created_at")
    search_fields = ("job__title", "job__slug", "ip")
