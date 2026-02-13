# apps/academics/admin.py
from django.contrib import admin
from .models import (
    AcademicLevel, AcademicSubject, AcademicSubjectMedia,
    AcademicCategory, AcademicChapter, AcademicMaterial, 
    AcademicMaterialTranslation, AcademicMaterialMedia
)


@admin.register(AcademicLevel)
class AcademicLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "board", "rank", "is_active")
    list_filter = ("board", "is_active")
    search_fields = ("name",)


class SubjectMediaInline(admin.TabularInline):
    model = AcademicSubjectMedia
    extra = 1


@admin.register(AcademicSubject)
class AcademicSubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "rank")
    list_filter = ("level",)
    search_fields = ("name",)
    inlines = [SubjectMediaInline]


@admin.register(AcademicChapter)
class AcademicChapterAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "rank", "is_active")
    list_filter = ("subject", "is_active")
    search_fields = ("name",)


@admin.register(AcademicCategory)
class AcademicCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "rank")
    search_fields = ("name",)


class TranslationInline(admin.TabularInline):
    model = AcademicMaterialTranslation
    extra = 1


class MaterialMediaInline(admin.TabularInline):
    model = AcademicMaterialMedia
    extra = 1


@admin.register(AcademicMaterial)
class AcademicMaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "category", "chapter", "material_type", "status", "position", "deleted_at")
    list_filter = ("subject", "category", "chapter", "material_type", "status", "deleted_at")
    search_fields = ("translations__title",)
    inlines = [TranslationInline, MaterialMediaInline]
    
    def get_queryset(self, request):
        # Allow admin to see deleted items clearly
        return super().get_queryset(request)
