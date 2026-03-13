from django.db import models


class Section(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    rank = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    # Rename old field to avoid conflict
    # section_name = models.CharField(max_length=50, blank=True)
    
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100) 
    slug = models.SlugField()
    language = models.CharField(max_length=5, default="te")

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    # Rich Content
    image = models.ForeignKey(
        "media.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="category_images"
    )
    pdf = models.ForeignKey(
        "media.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="category_pdfs"
    )
    content = models.TextField(blank=True, help_text="Rich text / HTML content")

    # sakshi-level controls
    rank = models.PositiveIntegerField(default=0)     # ordering in UI
    is_active = models.BooleanField(default=True)     # soft disable

    # audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("section", "slug", "parent")
        ordering = ["section", "rank", "name", "id"]
        indexes = [
            models.Index(fields=["section", "is_active", "parent"]),
            models.Index(fields=["section", "slug"]),
        ]

    def __str__(self):
        section_slug = self.section.slug if self.section else "no-section"
        return f"{section_slug}/{self.slug}"
