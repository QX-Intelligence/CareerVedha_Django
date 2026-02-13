from django.db import models


class AuditLog(models.Model):
    """
    Stores important events in CMS for tracking who did what.
    Bulletproof changes:
    ✅ user_id stored as string (JWT sub is usually string/uuid)
    ✅ entity_id stored as string (future-proof)
    ✅ metadata JSON for extra info
    ✅ indexed for performance
    """

    entity = models.CharField(max_length=50)  # "Article", "Job", "Category"
    entity_id = models.CharField(max_length=64)  # store int/uuid as string

    action = models.CharField(max_length=50)  # CREATE / UPDATE / REVIEW / PUBLISH / DEACTIVATE / DELETE

    user_id = models.CharField(max_length=255)  # JWT sub (string)
    role = models.CharField(max_length=20)

    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["entity", "entity_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["user_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity}({self.entity_id}) by {self.user_id}"
