from django.db import models
from django.utils.timezone import now
from apps.taxonomy.models import Category


class Article(models.Model):
    STATUS = [
        ("DRAFT", "Draft"),
        ("REVIEW", "Review"),
        ("SCHEDULED", "Scheduled"),
        ("PUBLISHED", "Published"),
        ("INACTIVE", "Inactive"),
    ]

    slug = models.SlugField()
    section = models.CharField(max_length=50)

    status = models.CharField(max_length=10, choices=STATUS, default="DRAFT")

    # Search-ready fields
    tags = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)

    # SEO
    canonical_url = models.URLField(blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    noindex = models.BooleanField(default=False)

    # OG
    og_title = models.CharField(max_length=255, blank=True)
    og_description = models.CharField(max_length=300, blank=True)
    og_image_url = models.URLField(blank=True)

    # Expiry (optional)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Audit
    created_by = models.CharField(max_length=255, blank=True, default="")
    updated_by = models.CharField(max_length=255, blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)

    # Analytics
    views_count = models.PositiveIntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = ("section", "slug")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["section", "slug"], name="article_section_slug_idx"),
            models.Index(fields=["status", "noindex"], name="article_status_noindex_idx"),
            models.Index(fields=["published_at"], name="article_published_at_idx"),
            models.Index(fields=["status", "section"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.section}/{self.slug} ({self.status})"

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < now())

    @property
    def prioritized_title(self):
        """
        Returns English title if available, then Telugu, then first available.
        Using .all() allows us to leverage prefetch_related cache easily.
        """
        trans = list(self.translations.all())
        # Try English first (case-insensitive)
        en = next((t for t in trans if t.language.lower().strip() == 'en'), None)
        if en: return en.title
        # Try Telugu second
        te = next((t for t in trans if t.language.lower().strip() == 'te'), None)
        if te: return te.title
        # Fallback to first available
        return trans[0].title if trans else ""

    @property
    def title(self):
        return self.prioritized_title


class ArticleTranslation(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="translations"
    )
    language = models.CharField(max_length=2)  # te / en
    title = models.CharField(max_length=255)
    content = models.TextField()  # HTML
    summary = models.TextField(blank=True) # Short excerpt

    class Meta:
        unique_together = ("article", "language")
        indexes = [
            models.Index(fields=["language"]),
        ]

    def __str__(self):
        return f"{self.article.section}/{self.article.slug} - {self.language}"


class ArticleCategory(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="article_categories"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="category_articles"
    )

    class Meta:
        unique_together = ("article", "category")
        indexes = [
            models.Index(fields=["category", "article"]),
        ]

    def __str__(self):
        return f"{self.article_id} -> {self.category_id}"


class ArticleFeature(models.Model):
    FEATURE_CHOICES = [
        ("HERO", "Hero Slider"),
        ("TOP", "Top Stories"),
        ("BREAKING", "Breaking"),
        ("EDITOR_PICK", "Editor Pick"),
        ("MUST_READ", "Must Read"),
    ]

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="features"
    )
    feature_type = models.CharField(max_length=20, choices=FEATURE_CHOICES)

    # "" => global homepage, "academics" => academics homepage
    section = models.CharField(max_length=50, blank=True, default="")

    rank = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["rank", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["article", "feature_type", "section"],
                name="uniq_article_feature_per_section",
            )
        ]
        indexes = [
            models.Index(fields=["feature_type", "section", "rank"]),
            models.Index(fields=["is_active"]),
        ]

    def is_live(self):
        t = now()
        if not self.is_active:
            return False
        if self.start_at and self.start_at > t:
            return False
        if self.end_at and self.end_at < t:
            return False
        return True

    def __str__(self):
        return f"{self.feature_type}:{self.section} -> {self.article.slug}"


class ArticleRevision(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="revisions"
    )
    language = models.CharField(max_length=2)
    title = models.CharField(max_length=255)
    content = models.TextField()
    summary = models.TextField(blank=True)

    editor_user_id = models.CharField(max_length=255, blank=True, default="")
    note = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["article", "language", "created_at"]),
        ]

    def __str__(self):
        return f"REV {self.article_id} {self.language} {self.created_at}"


class ArticleMedia(models.Model):
    USAGE = [
        ("BANNER", "Banner"),
        ("MAIN", "Main"),
        ("INLINE", "Inline"),
        ("GALLERY", "Gallery"),
        ("ATTACHMENT", "Attachment"),
    ]

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="media_links",
    )

    # 🔗 Integrated Media (FK)
    media = models.ForeignKey(
        "media.MediaAsset",
        on_delete=models.CASCADE,
        related_name="article_links",
        null=True  # Temporary for migration
    )

    usage = models.CharField(max_length=20, choices=USAGE)
    position = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["usage", "position"]
        indexes = [
            models.Index(fields=["article", "usage"]),
            models.Index(fields=["media"]),
        ]
        unique_together = ("article", "media", "usage")

    def __str__(self):
        return f"{self.article_id} -> media:{self.media.id} ({self.usage})"
