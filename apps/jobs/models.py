from django.db import models
from django.utils.timezone import now


class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ("GOVT", "Government"),
        ("PRIVATE", "Private"),
    ]

    STATUS_CHOICES = [
        (0, "Inactive"),
        (1, "Active"),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    job_type = models.CharField(max_length=10, choices=JOB_TYPE_CHOICES)

    department = models.CharField(max_length=255, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)

    qualification = models.CharField(max_length=255, blank=True)
    experience = models.CharField(max_length=255, blank=True)
    vacancies = models.PositiveIntegerField(default=0)

    application_start_date = models.DateField(null=True, blank=True)
    application_end_date = models.DateField()

    exam_date = models.DateField(null=True, blank=True)

    job_description = models.TextField()
    eligibility = models.TextField(blank=True)
    selection_process = models.TextField(blank=True)
    salary = models.CharField(max_length=255, blank=True)

    apply_url = models.URLField(blank=True)

    # ✅ Job Status: 0 = Inactive, 1 = Active
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)

    # ✅ trending fast (NO JOIN REQUIRED)
    views_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["application_end_date"]),
            models.Index(fields=["job_type"]),
            models.Index(fields=["location"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["views_count"]),  # ✅ trending
        ]

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        return self.application_end_date < now().date()


class JobViewEvent(models.Model):
    """
    Tracks job views (analytics)
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="view_events")
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["job", "created_at"]),
        ]
