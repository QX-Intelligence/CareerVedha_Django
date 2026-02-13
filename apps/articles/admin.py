from django.contrib import admin
from .models import Article, ArticleTranslation

class TranslationInline(admin.TabularInline):
    model = ArticleTranslation
    extra = 0

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "section",
        "status",
        "created_at",
        "public_url",
    )

    list_filter = ("section", "status", "created_at")
    search_fields = ("slug",)
    inlines = [TranslationInline]

    readonly_fields = ("created_at",)

    def public_url(self, obj):
        return f"/{obj.section}/{obj.slug}/"
