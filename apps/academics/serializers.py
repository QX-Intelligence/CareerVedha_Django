from rest_framework import serializers
from django.db import transaction
from django.conf import settings
from .models import (
    AcademicLevel, AcademicSubject, AcademicSubjectMedia, 
    AcademicCategory, AcademicChapter, 
    AcademicMaterial, AcademicMaterialTranslation, AcademicMaterialMedia
)
from apps.media.s3 import get_s3_client
from apps.media.utils import upload_media_file, detect_media_type
from apps.media.models import MediaAsset
from .cache import bump_academics_cache
import uuid


class AcademicLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicLevel
        fields = "__all__"

    def create(self, validated_data):
        instance = super().create(validated_data)
        bump_academics_cache()
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        bump_academics_cache()
        return instance


class AcademicSubjectMediaSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = AcademicSubjectMedia
        fields = ("id", "media", "media_url", "usage", "position")

    def get_media_url(self, obj):
        if obj.media:
            from apps.media.utils import get_media_url
            return get_media_url(obj.media)
        return None


# AcademicChapterTranslationSerializer removed. Use AcademicMaterialSerializer for content.


class AcademicChapterSerializer(serializers.ModelSerializer):
    """
    Chapter folder metadata.
    Supports "One-Shot" creation/update of the Chapter's primary Intro Material.
    """
    # Bilingual Intro Content (Write-only)
    eng_title = serializers.CharField(write_only=True, required=False, allow_blank=True)
    eng_summary = serializers.CharField(write_only=True, required=False, allow_blank=True)
    eng_content = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tel_title = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tel_summary = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tel_content = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # Intro Media (Write-only)
    banner_file = serializers.FileField(write_only=True, required=False)
    banner_media_id = serializers.IntegerField(write_only=True, required=False)
    document_file = serializers.FileField(write_only=True, required=False)
    document_media_id = serializers.IntegerField(write_only=True, required=False)
    
    # Generic attachments
    attachments = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    media_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    # Read-only intro view
    introduction = serializers.SerializerMethodField()

    class Meta:
        model = AcademicChapter
        fields = (
            "id", "subject", "name", "rank", "is_active",
            "eng_title", "eng_summary", "eng_content", "tel_title", "tel_summary", "tel_content",
            "banner_file", "banner_media_id", "document_file", "document_media_id",
            "attachments", "media_ids", "introduction"
        )

    def get_introduction(self, obj):
        intro = obj.introduction
        if intro:
            # Avoid circular import issues if any, but since it's in the same file it's fine
            return AcademicMaterialSerializer(intro, context=self.context).data
        return None

    def _sync_intro_material(self, chapter, validated_data):
        """Creates or updates the primary introduction material for this chapter."""
        # Check if we have any intro data to sync
        intro_fields = [
            "eng_title", "eng_summary", "eng_content", "tel_title", "tel_summary", "tel_content",
            "banner_file", "banner_media_id", "document_file", "document_media_id",
            "attachments", "media_ids"
        ]
        if not any(k in validated_data for k in intro_fields):
            return

        # Prepare material data
        material_data = {
            "subject": chapter.subject.id,
            "chapter": chapter.id,
            "material_type": "CONTENT",
            "status": "PUBLISHED",
            "position": 0, # Intros always come first
        }
        
        # Transfer the extra fields
        for field in intro_fields:
            if field in validated_data:
                material_data[field] = validated_data.get(field)

        # Get existing intro or create new
        intro = chapter.introduction
        material_serializer = AcademicMaterialSerializer(
            instance=intro, 
            data=material_data, 
            partial=True if intro else False,
            context=self.context
        )
        material_serializer.is_valid(raise_exception=True)
        material_serializer.save()

    @transaction.atomic
    def create(self, validated_data):
        intro_data = {k: validated_data.pop(k) for k in list(validated_data.keys()) if k in [
            "eng_title", "eng_summary", "eng_content", "tel_title", "tel_summary", "tel_content",
            "banner_file", "banner_media_id", "document_file", "document_media_id",
            "attachments", "media_ids"
        ]}
        
        chapter = AcademicChapter.objects.create(**validated_data)
        if intro_data:
            self._sync_intro_material(chapter, intro_data)
        
        bump_academics_cache()
        return chapter

    @transaction.atomic
    def update(self, instance, validated_data):
        intro_data = {k: validated_data.pop(k) for k in list(validated_data.keys()) if k in [
            "eng_title", "eng_summary", "eng_content", "tel_title", "tel_summary", "tel_content",
            "banner_file", "banner_media_id", "document_file", "document_media_id",
            "attachments", "media_ids"
        ]}
        
        chapter = super().update(instance, validated_data)
        if intro_data:
            self._sync_intro_material(chapter, intro_data)
        
        bump_academics_cache()
        return chapter


class AcademicChapterDetailSerializer(serializers.ModelSerializer):
    """Chapter folder + its Intro Material + subsequent Materials."""
    introduction = serializers.SerializerMethodField()
    materials = serializers.SerializerMethodField()

    class Meta:
        model = AcademicChapter
        fields = ("id", "subject", "name", "rank", "is_active", "introduction", "materials")

    def get_introduction(self, obj):
        intro = obj.introduction
        # Public view: Only show published and non-deleted
        if intro and intro.status == "PUBLISHED" and not intro.deleted_at:
            return AcademicMaterialSerializer(intro, context=self.context).data
        return None

    def get_materials(self, obj):
        # Nested Material List
        materials = obj.materials.filter(status="PUBLISHED", deleted_at__isnull=True).order_by("position", "-created_at")
        return AcademicMaterialSerializer(materials, many=True, context=self.context).data


class AcademicSubjectSerializer(serializers.ModelSerializer):
    media_links = AcademicSubjectMediaSerializer(many=True, read_only=True)
    chapters = AcademicChapterSerializer(many=True, read_only=True)
    
    # 🖼️ Media write fields
    icon_file = serializers.FileField(write_only=True, required=False)
    icon_media_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = AcademicSubject
        fields = ("id", "level", "name", "rank", "media_links", "chapters", "icon_file", "icon_media_id")

    def _handle_media(self, subject, icon_file, icon_media_id, is_update=False):
        from apps.media.models import MediaAsset
        from apps.media.utils import detect_media_type
        from apps.media.s3 import get_s3_client
        import uuid
        from django.conf import settings

        if is_update and (icon_file or icon_media_id):
            AcademicSubjectMedia.objects.filter(subject=subject, usage="ICON").delete()

        if icon_file:
            asset = upload_media_file(
                file_obj=icon_file,
                prefix="academics/subject",
                purpose="academics",
                user_id=None, # System/Anonymous update unless session context passed
                section=str(subject.id)
            )
            
            AcademicSubjectMedia.objects.create(
                subject=subject,
                media=asset,
                usage="ICON",
                position=0
            )

        if icon_media_id:
            try:
                asset = MediaAsset.objects.get(id=icon_media_id)
                AcademicSubjectMedia.objects.get_or_create(
                    subject=subject,
                    media=asset,
                    usage="ICON",
                    defaults={"position": 1 if icon_file else 0}
                )
            except MediaAsset.DoesNotExist:
                pass

    @transaction.atomic
    def create(self, validated_data):
        icon_file = validated_data.pop("icon_file", None)
        icon_media_id = validated_data.pop("icon_media_id", None)
        
        subject = AcademicSubject.objects.create(**validated_data)
        if icon_file or icon_media_id:
            self._handle_media(subject, icon_file, icon_media_id)
        
        bump_academics_cache()
        # Pre-load level and media for representation
        return AcademicSubject.objects.select_related("level").prefetch_related("media_links__media").get(id=subject.id)

    @transaction.atomic
    def update(self, instance, validated_data):
        icon_file = validated_data.pop("icon_file", None)
        icon_media_id = validated_data.pop("icon_media_id", None)
        
        subject = super().update(instance, validated_data)
        if icon_file or icon_media_id:
            self._handle_media(subject, icon_file, icon_media_id, is_update=True)
        
        bump_academics_cache()
        return subject


class AcademicCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicCategory
        fields = "__all__"


class AcademicMaterialTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicMaterialTranslation
        fields = ("language", "title", "summary", "content")


class AcademicMaterialMediaSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = AcademicMaterialMedia
        fields = ("id", "media", "media_url", "thumbnail_url", "usage", "position")

    def get_media_url(self, obj):
        if obj.media:
            from apps.media.utils import get_media_url
            return get_media_url(obj.media)
        return None

    def get_thumbnail_url(self, obj):
        return self.get_media_url(obj)


class AcademicMaterialSerializer(serializers.ModelSerializer):
    translations = AcademicMaterialTranslationSerializer(many=True, read_only=True)
    media_links = AcademicMaterialMediaSerializer(many=True, read_only=True)
    
    chapter_name = serializers.ReadOnlyField(source="chapter.name")

    # Bilingual write fields
    eng_title = serializers.CharField(write_only=True, required=False, allow_blank=True)
    eng_summary = serializers.CharField(write_only=True, required=False, allow_blank=True)
    eng_content = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tel_title = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tel_summary = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tel_content = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # 🖼️ Media/File write fields
    banner_file = serializers.FileField(write_only=True, required=False)
    banner_media_id = serializers.IntegerField(write_only=True, required=False)
    document_file = serializers.FileField(write_only=True, required=False)
    document_media_id = serializers.IntegerField(write_only=True, required=False)
    
    # Generic attachments (images, etc)
    attachments = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    media_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = AcademicMaterial
        fields = (
            "id", "subject", "category", "chapter", "chapter_name",
            "material_type", "external_url", "status", "position",
            "created_by", "updated_by", "created_at", "updated_at",
            "deleted_at", "translations", "media_links",
            "eng_title", "eng_summary", "eng_content", "tel_title", "tel_summary", "tel_content",
            "banner_file", "banner_media_id", "document_file", "document_media_id",
            "attachments", "media_ids"
        )
        read_only_fields = ("id", "created_by", "updated_by", "created_at", "updated_at", "deleted_at")

    def _handle_media(self, material, banner_file, document_file, banner_media_id, document_media_id, attachments=None, media_ids=None, is_update=False):
        if is_update:
            if banner_file or banner_media_id:
                AcademicMaterialMedia.objects.filter(material=material, usage="BANNER").delete()
            if document_file or document_media_id:
                AcademicMaterialMedia.objects.filter(material=material, usage="DOCUMENT").delete()
            if attachments or media_ids:
                AcademicMaterialMedia.objects.filter(material=material, usage="ATTACHMENT").delete()
        
        # Helper for direct upload
        def upload_and_link(file_obj, usage):
            asset = upload_media_file(
                file_obj=file_obj,
                prefix="academics",
                purpose="academics",
                user_id=material.created_by,
                section=str(material.id)
            )
            AcademicMaterialMedia.objects.create(material=material, media=asset, usage=usage, position=0)

        # Helper for linking existing ID
        def link_id(media_id, usage, position=0):
            try:
                asset = MediaAsset.objects.get(id=media_id)
                AcademicMaterialMedia.objects.get_or_create(
                    material=material, media=asset, usage=usage,
                    defaults={"position": position}
                )
            except MediaAsset.DoesNotExist:
                pass

        if banner_file: upload_and_link(banner_file, "BANNER")
        if banner_media_id: link_id(banner_media_id, "BANNER", position=1 if banner_file else 0)
        if document_file: upload_and_link(document_file, "DOCUMENT")
        if document_media_id: link_id(document_media_id, "DOCUMENT", position=1 if document_file else 0)
        
        # Process multiple attachments
        if attachments:
            for f in attachments:
                upload_and_link(f, "ATTACHMENT")
        if media_ids:
            for mid in media_ids:
                link_id(mid, "ATTACHMENT")

    @transaction.atomic
    def create(self, validated_data):
        # Pop fields
        eng_title = validated_data.pop("eng_title", "").strip()
        eng_summary = validated_data.pop("eng_summary", "").strip()
        eng_content = validated_data.pop("eng_content", "").strip()
        tel_title = validated_data.pop("tel_title", "").strip()
        tel_summary = validated_data.pop("tel_summary", "").strip()
        tel_content = validated_data.pop("tel_content", "").strip()

        banner_file = validated_data.pop("banner_file", None)
        banner_media_id = validated_data.pop("banner_media_id", None)
        document_file = validated_data.pop("document_file", None)
        document_media_id = validated_data.pop("document_media_id", None)
        attachments = validated_data.pop("attachments", None)
        media_ids = validated_data.pop("media_ids", None)

        user_id = self.context.get("user_id", "system")
        validated_data["created_by"] = str(user_id)
        validated_data["updated_by"] = str(user_id)

        material = AcademicMaterial.objects.create(**validated_data)

        # Bulk create translations for performance
        translations = []
        if eng_title:
            translations.append(AcademicMaterialTranslation(
                material=material, language="en", title=eng_title, summary=eng_summary, content=eng_content
            ))
        if tel_title:
            translations.append(AcademicMaterialTranslation(
                material=material, language="te", title=tel_title, summary=tel_summary, content=tel_content
            ))
        if translations:
            AcademicMaterialTranslation.objects.bulk_create(translations)

        # Handle Media
        self._handle_media(material, banner_file, document_file, banner_media_id, document_media_id, attachments, media_ids)

        bump_academics_cache()
        # Pre-load for lightning fast representation
        return AcademicMaterial.objects.select_related(
            "subject", "category", "chapter"
        ).prefetch_related(
            "translations", "media_links__media"
        ).get(id=material.id)

    @transaction.atomic
    def update(self, instance, validated_data):
        eng_title = validated_data.pop("eng_title", "").strip()
        eng_summary = validated_data.pop("eng_summary", "").strip()
        eng_content = validated_data.pop("eng_content", "").strip()
        tel_title = validated_data.pop("tel_title", "").strip()
        tel_summary = validated_data.pop("tel_summary", "").strip()
        tel_content = validated_data.pop("tel_content", "").strip()

        banner_file = validated_data.pop("banner_file", None)
        banner_media_id = validated_data.pop("banner_media_id", None)
        document_file = validated_data.pop("document_file", None)
        document_media_id = validated_data.pop("document_media_id", None)
        attachments = validated_data.pop("attachments", None)
        media_ids = validated_data.pop("media_ids", None)

        user_id = self.context.get("user_id", "system")
        validated_data["updated_by"] = str(user_id)

        # Update translations
        if eng_title:
            AcademicMaterialTranslation.objects.update_or_create(
                material=instance, language="en",
                defaults={"title": eng_title, "summary": eng_summary, "content": eng_content}
            )
        if tel_title:
            AcademicMaterialTranslation.objects.update_or_create(
                material=instance, language="te",
                defaults={"title": tel_title, "summary": tel_summary, "content": tel_content}
            )

        material = super().update(instance, validated_data)

        self._handle_media(material, banner_file, document_file, banner_media_id, document_media_id, attachments, media_ids, is_update=True)

        bump_academics_cache()
        return material


class ExamChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicChapter
        fields = ("id", "name")


class ExamSubjectSerializer(serializers.ModelSerializer):
    chapters = ExamChapterSerializer(many=True, read_only=True)

    class Meta:
        model = AcademicSubject
        fields = ("id", "name", "chapters")


class ExamHierarchySerializer(serializers.ModelSerializer):
    subjects = ExamSubjectSerializer(many=True, read_only=True)

    class Meta:
        model = AcademicLevel
        fields = ("id", "name", "board", "subjects")