# apps/media/models.py
from django.db import models
from django.utils.timezone import now


class MediaAsset(models.Model):
    PURPOSE_CHOICES = [
        ("article", "Article"),
        ("academics", "Academics"),
        ("jobs", "Jobs"),
        ("general", "General"),
    ]

    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("pdf", "PDF"),
        ("doc", "Document"),
        ("video", "Video"),
    ]

    # Map extensions to media_type choices
    MEDIA_TYPE_EXTENSIONS = {
        "image": [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"],
        "pdf": [".pdf"],
        "doc": [".doc", ".docx", ".txt", ".rtf"],
        "video": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
    }

    # 🔑 storage (S3 key only)
    file_key = models.CharField(max_length=500, unique=True)
    file_size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=100)

    # 🧠 metadata
    title = models.CharField(max_length=255)
    alt_text = models.CharField(max_length=255, blank=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default="general",
    )
    section = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=5, default="en")

    # 👤 audit
    uploaded_by_user_id = models.CharField(max_length=100)
    uploaded_by_role = models.CharField(max_length=20)

    # ♻ lifecycle
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["purpose", "section"]),
            models.Index(fields=["media_type"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = now()
        self.save(update_fields=["is_deleted", "is_active", "deleted_at"])

    def __str__(self):
        return f"{self.media_type} | {self.title}"
