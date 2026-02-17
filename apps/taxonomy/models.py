from django.db import models


class Category(models.Model):
    section = models.CharField(
        max_length=50,
        help_text="academics | exams | news | more | campus-pages"
    )

    name = models.CharField(max_length=100) 
    slug = models.SlugField()

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    #  sakshi-level controls
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
        return f"{self.section}/{self.slug}"
