from django.contrib.sitemaps import Sitemap
from django.utils.timezone import now
from .models import Article

class ArticleSitemap(Sitemap):
    def items(self):
        return Article.objects.filter(status="PUBLISHED", noindex=False, published_at__lte=now())

    def location(self, obj):
        return f"/{obj.section}/{obj.slug}/"
