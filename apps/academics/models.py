# apps/academics/models.py
from django.db import models
from django.utils.timezone import now
from apps.media.models import MediaAsset


class AcademicLevel(models.Model):
    BOARD_CHOICES = [
        ("AP", "Andhra Pradesh"),
        ("TS", "Telangana"),
        ("CBSE", "CBSE"),
        ("NONE", "None"),
    ]

    name = models.CharField(max_length=100)  # 10th Class, Intermediate, B.Tech
    board = models.CharField(max_length=10, choices=BOARD_CHOICES, default="NONE")
    
    rank = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["rank", "name"]

    def __str__(self):
        return f"{self.name} ({self.board})"


class AcademicSubject(models.Model):
    level = models.ForeignKey(
        AcademicLevel, on_delete=models.CASCADE, related_name="subjects"
    )
    name = models.CharField(max_length=100)
    
    rank = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["rank", "name"]

    def __str__(self):
        return f"{self.level.name} - {self.name}"


class AcademicSubjectMedia(models.Model):
    """Support for multi-images/icons per subject."""
    subject = models.ForeignKey(
        AcademicSubject, on_delete=models.CASCADE, related_name="media_links"
    )
    media = models.ForeignKey(MediaAsset, on_delete=models.CASCADE)
    usage = models.CharField(max_length=50, default="ICON")  # ICON, BANNER, etc.
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]


class AcademicChapter(models.Model):
    subject = models.ForeignKey(
        AcademicSubject, on_delete=models.CASCADE, related_name="chapters"
    )
    name = models.CharField(max_length=150)
    rank = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["rank", "id"]

    def __str__(self):
        return f"{self.subject.name} / {self.name}"

    @property
    def introduction(self):
        """Fetches the primary content-type material for this chapter (agnostic of status)."""
        return self.materials.filter(material_type="CONTENT", deleted_at__isnull=True).first()


# AcademicChapterTranslation deleted in refactor. Content moved to AcademicMaterial.


class AcademicCategory(models.Model):
    """Study Material, Previous Papers, Syllabus, Bit Bank, etc."""
    name = models.CharField(max_length=100)
    rank = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["rank", "name"]

    def __str__(self):
        return self.name


class AcademicMaterial(models.Model):
    TYPE_CHOICES = [
        ("DOCUMENT", "Document/PDF"),
        ("IMAGE", "Image/Infographic"),
        ("LINK", "External Link"),
        ("EXAM", "Online Exam"),
        ("CONTENT", "HTML Content"),
    ]

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
    ]

    # Level is redundant (traverse Subject -> Level)
    subject = models.ForeignKey(AcademicSubject, on_delete=models.CASCADE, related_name="materials")
    category = models.ForeignKey(AcademicCategory, on_delete=models.CASCADE, related_name="materials", null=True, blank=True)
    chapter = models.ForeignKey(AcademicChapter, on_delete=models.SET_NULL, null=True, blank=True, related_name="materials")
    
    material_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="CONTENT")
    external_url = models.URLField(blank=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="DRAFT")
    
    # Sequence control
    position = models.PositiveIntegerField(default=0)

    # Audit & Soft Delete
    created_by = models.CharField(max_length=255, blank=True, default="")
    updated_by = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "-created_at"]

    def __str__(self):
        return f"{self.id} ({self.status})"

    @property
    def title(self):
        """Intelligent title resolution."""
        trans = list(self.translations.all())
        en = next((t for t in trans if t.language == 'en'), None)
        if en: return en.title
        te = next((t for t in trans if t.language == 'te'), None)
        if te: return te.title
        return trans[0].title if trans else f"Material {self.id}"

    def soft_delete(self):
        self.deleted_at = now()
        self.save(update_fields=["deleted_at"])


class AcademicMaterialTranslation(models.Model):
    material = models.ForeignKey(
        AcademicMaterial, on_delete=models.CASCADE, related_name="translations"
    )
    language = models.CharField(max_length=2)  # te / en
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True) # Added for card previews
    content = models.TextField(blank=True)

    class Meta:
        unique_together = ("material", "language")

    def __str__(self):
        return f"{self.material.id} - {self.language}"


class AcademicMaterialMedia(models.Model):
    """Support for multiple PDF documents, images, and model papers."""
    USAGE_CHOICES = [
        ("BANNER", "Banner Image"),
        ("INLINE", "Inline Image"),
        ("DOCUMENT", "Study Material"),
        ("MODEL_PAPER", "Model Paper/Previous Paper"),
        ("ATTACHMENT", "General Attachment"),
    ]
    
    material = models.ForeignKey(
        AcademicMaterial, on_delete=models.CASCADE, related_name="media_links"
    )
    media = models.ForeignKey(MediaAsset, on_delete=models.CASCADE)
    usage = models.CharField(max_length=20, choices=USAGE_CHOICES, default="DOCUMENT")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
