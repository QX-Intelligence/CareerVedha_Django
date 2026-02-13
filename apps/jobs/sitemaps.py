from django.contrib.sitemaps import Sitemap
from django.utils.timezone import now
from .models import Job


class JobsSitemap(Sitemap):
    """
    Sitemap for all active, non-expired job postings
    Helps Google discover and index all job listings
    """
    changefreq = "daily"
    priority = 0.8
    def items(self):
        today = now().date()
        return Job.objects.filter(
            status=1,  # Active jobs only
            application_end_date__gte=today,
        ).order_by("-created_at")

    def location(self, obj):
        return f"/jobs/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at
