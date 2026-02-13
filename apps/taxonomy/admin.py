from django.contrib import admin
from .models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("section", "slug", "parent")
    list_filter = ("section",)
    search_fields = ("slug", "name")
