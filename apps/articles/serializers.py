from rest_framework import serializers
from .models import Article, ArticleTranslation, ArticleCategory, ArticleMedia
from apps.media.models import MediaAsset
from apps.media.utils import upload_media_file, detect_media_type
from apps.media.s3 import get_s3_client
from django.conf import settings
import uuid


class ArticleMediaSerializer(serializers.ModelSerializer):
    media_id = serializers.PrimaryKeyRelatedField(
        source="media",
        queryset=MediaAsset.objects.all(),
        write_only=True
    )
    media_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ArticleMedia
        fields = ("id", "media_id", "media_details", "usage", "position", "created_at")

    def get_media_details(self, obj):
        if obj.media:
            from apps.media.utils import get_media_url
            return {
                "id": obj.media.id,
                "title": obj.media.title,
                "url": get_media_url(obj.media),
                "media_type": "banner" if obj.usage == "BANNER" else obj.media.media_type
            }
        return None


class PublicArticleMediaSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = ArticleMedia
        fields = ("media_url", "usage", "position")

    def get_media_url(self, obj):
        if obj.media:
            from apps.media.utils import get_media_url
            return get_media_url(obj.media)
        return None


class ArticleTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleTranslation
        fields = ("language", "title", "content", "summary")


class ArticleCategoryDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='category.id')
    name = serializers.CharField(source='category.name')
    section = serializers.CharField(source='category.section')
    slug = serializers.CharField(source='category.slug')
    is_active = serializers.BooleanField(source='category.is_active')

    class Meta:
        model = ArticleCategory
        fields = ("id", "name", "section", "slug", "is_active")


class ArticleSerializer(serializers.ModelSerializer):
    translations = ArticleTranslationSerializer(many=True, required=False)
    media_links = ArticleMediaSerializer(many=True, read_only=True)
    title = serializers.CharField(read_only=True)

    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    categories = ArticleCategoryDetailSerializer(source='article_categories', many=True, read_only=True)
    
    # Direct English fields
    eng_title = serializers.CharField(write_only=True, required=False, allow_blank=True)
    eng_content = serializers.CharField(write_only=True, required=False, allow_blank=True)
    eng_summary = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Direct Telugu fields
    tel_title = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tel_content = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tel_summary = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # 🖼️ Unified Media Upload
    banner_file = serializers.FileField(write_only=True, required=False)
    banner_media_id = serializers.IntegerField(write_only=True, required=False)
    main_file = serializers.FileField(write_only=True, required=False)
    main_media_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Article
        fields = (
            "id",
            "slug",
            "title",
            "section",
            "status",
            "tags",
            "keywords",

            "canonical_url",
            "meta_title",
            "meta_description",
            "noindex",

            "og_title",
            "og_description",
            "og_image_url",

            "expires_at",

            "created_by",
            "updated_by",
            "published_at",

            "views_count",
            "last_viewed_at",

            "created_at",
            "updated_at",

            "translations",
            "media_links",
            "category_ids",
            "categories",

            "eng_title",
            "eng_content",
            "eng_summary",
            "tel_title",
            "tel_content",
            "tel_summary",
            "banner_file",
            "banner_media_id",
            "main_file",
            "main_media_id",
        )
        read_only_fields = (
            "id",
            "status",
            "created_by",
            "updated_by",
            "published_at",
            "views_count",
            "last_viewed_at",
            "created_at",
            "updated_at",
        )

    def get_title(self, obj):
        return obj.title

    def validate_translations(self, value):
        langs = [t.get("language") for t in value]
        if len(langs) != len(set(langs)):
            raise serializers.ValidationError("Duplicate translation language found")
        return value

    def create(self, validated_data):
        translations_data = validated_data.pop("translations", [])
        category_ids = validated_data.pop("category_ids", [])
        
        # Extract direct language fields
        eng_title = validated_data.pop("eng_title", "").strip()
        eng_content = validated_data.pop("eng_content", "").strip()
        eng_summary = validated_data.pop("eng_summary", "").strip()
        tel_title = validated_data.pop("tel_title", "").strip()
        tel_content = validated_data.pop("tel_content", "").strip()
        tel_summary = validated_data.pop("tel_summary", "").strip()

        # Pop media fields BEFORE article creation
        banner_file = validated_data.pop("banner_file", None)
        banner_media_id = validated_data.pop("banner_media_id", None)
        main_file = validated_data.pop("main_file", None)
        main_media_id = validated_data.pop("main_media_id", None)

        article = Article.objects.create(**validated_data)

        # Create translations from nested data
        for tr in translations_data:
            lang = tr.pop("language", None)
            if lang:
                ArticleTranslation.objects.update_or_create(
                    article=article, language=lang, defaults=tr
                )
        
        # 🖼️ Handle Banner File (Direct Upload)
        if banner_file:
            asset = upload_media_file(
                file_obj=banner_file,
                prefix="article",
                purpose="article",
                user_id=article.created_by,
                section=article.section
            )
            ArticleMedia.objects.create(article=article, media=asset, usage="BANNER", position=0)

        # 🔗 Handle Existing Banner Media ID
        if banner_media_id:
            try:
                asset = MediaAsset.objects.get(id=banner_media_id)
                ArticleMedia.objects.get_or_create(
                    article=article, media=asset, usage="BANNER", 
                    defaults={"position": 1 if banner_file else 0}
                )
            except MediaAsset.DoesNotExist: pass

        # 🖼️ Handle Main File (Direct Upload)
        if main_file:
            asset = upload_media_file(
                file_obj=main_file,
                prefix="article",
                purpose="article",
                user_id=article.created_by,
                section=article.section
            )
            ArticleMedia.objects.create(article=article, media=asset, usage="MAIN", position=0)

        # 🔗 Handle Existing Main Media ID
        if main_media_id:
            try:
                asset = MediaAsset.objects.get(id=main_media_id)
                ArticleMedia.objects.get_or_create(
                    article=article, media=asset, usage="MAIN", 
                    defaults={"position": 1 if main_file else 0}
                )
            except MediaAsset.DoesNotExist: pass

        # Create English translation if provided
        if eng_title and (eng_content or eng_summary):
            ArticleTranslation.objects.update_or_create(
                article=article,
                language="en",
                defaults={
                    "title": eng_title,
                    "content": eng_content,
                    "summary": eng_summary
                }
            )
        
        # Create Telugu translation if provided
        if tel_title and (tel_content or tel_summary):
            ArticleTranslation.objects.update_or_create(
                article=article,
                language="te",
                defaults={
                    "title": tel_title,
                    "content": tel_content,
                    "summary": tel_summary
                }
            )

        for cid in category_ids:
            ArticleCategory.objects.get_or_create(article=article, category_id=cid)

        return article

    def update(self, instance, validated_data):
        translations_data = validated_data.pop("translations", [])
        category_ids = validated_data.pop("category_ids", None)
        
        # Extract direct language fields
        eng_title = validated_data.pop("eng_title", "").strip()
        eng_content = validated_data.pop("eng_content", "").strip()
        eng_summary = validated_data.pop("eng_summary", "").strip()
        tel_title = validated_data.pop("tel_title", "").strip()
        tel_content = validated_data.pop("tel_content", "").strip()
        tel_summary = validated_data.pop("tel_summary", "").strip()

        # Pop media fields BEFORE update loop
        banner_file = validated_data.pop("banner_file", None)
        banner_media_id = validated_data.pop("banner_media_id", None)
        main_file = validated_data.pop("main_file", None)
        main_media_id = validated_data.pop("main_media_id", None)

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or Create English translation
        if eng_title:
            tr, created = ArticleTranslation.objects.get_or_create(
                article=instance, language="en",
                defaults={"title": eng_title, "content": eng_content, "summary": eng_summary}
            )
            if not created:
                tr.title = eng_title
                tr.content = eng_content
                tr.summary = eng_summary
                tr.save()

        # Update or Create Telugu translation
        if tel_title:
            tr, created = ArticleTranslation.objects.get_or_create(
                article=instance, language="te",
                defaults={"title": tel_title, "content": tel_content, "summary": tel_summary}
            )
            if not created:
                tr.title = tel_title
                tr.content = tel_content
                tr.summary = tel_summary
                tr.save()

        # Handle Banner File / Media ID in update
        if banner_file or banner_media_id:
            # If we are providing ANY new banner info, we clear the old ones.
            ArticleMedia.objects.filter(article=instance, usage="BANNER").delete()
            
            if banner_file:
                asset = upload_media_file(
                    file_obj=banner_file,
                    prefix="article",
                    purpose="article",
                    user_id=instance.updated_by or instance.created_by,
                    section=instance.section
                )
                ArticleMedia.objects.create(
                    article=instance,
                    media=asset,
                    usage="BANNER",
                    position=0
                )

            if banner_media_id:
                try:
                    asset = MediaAsset.objects.get(id=banner_media_id)
                    ArticleMedia.objects.create(
                        article=instance,
                        media=asset,
                        usage="BANNER",
                        position=1 if banner_file else 0
                    )
                except MediaAsset.DoesNotExist:
                    pass

        # Handle Main File / Media ID in update
        if main_file or main_media_id:
            # Clear old MAIN entries if providing new ones
            ArticleMedia.objects.filter(article=instance, usage="MAIN").delete()
            
            if main_file:
                asset = upload_media_file(
                    file_obj=main_file,
                    prefix="article",
                    purpose="article",
                    user_id=instance.updated_by or instance.created_by,
                    section=instance.section
                )
                ArticleMedia.objects.create(
                    article=instance,
                    media=asset,
                    usage="MAIN",
                    position=0
                )

            if main_media_id:
                try:
                    asset = MediaAsset.objects.get(id=main_media_id)
                    ArticleMedia.objects.create(
                        article=instance,
                        media=asset,
                        usage="MAIN",
                        position=1 if main_file else 0
                    )
                except MediaAsset.DoesNotExist:
                    pass

        # Sync categories if provided
        if category_ids is not None:
            # Remove categories not in the list
            ArticleCategory.objects.filter(article=instance).exclude(category_id__in=category_ids).delete()
            # Add new categories
            for cid in category_ids:
                ArticleCategory.objects.get_or_create(article=instance, category_id=cid)

        # Handle nested translations (if any)
        for tr_data in translations_data:
            lang = tr_data.get("language")
            if lang:
                tr, created = ArticleTranslation.objects.get_or_create(
                    article=instance, language=lang,
                    defaults=tr_data
                )
                if not created:
                    for attr, value in tr_data.items():
                        setattr(tr, attr, value)
                    tr.save()

        return instance


class PublicArticleDetailSerializer(serializers.ModelSerializer):
    media = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id",
            "slug",
            "section",
            "title",
            "content",
            "summary",
            "tags",
            "keywords",
            "canonical_url",
            "noindex",
            "og_title",
            "og_description",
            "og_image_url",
            "published_at",
            "created_at",
            "updated_at",
            "media",
        )

    def get_title(self, obj):
        # Cache translation to avoid duplicate lookups
        if not hasattr(self, '_cached_translation'):
            lang = self.context.get("lang", "te")
            tr = obj.translations.filter(language=lang).first()
            if not tr:
                tr = obj.translations.filter(language="te").first()
            self._cached_translation = tr
        return self._cached_translation.title if self._cached_translation else ""

    def get_content(self, obj):
        # Reuse cached translation from get_title
        if not hasattr(self, '_cached_translation'):
            lang = self.context.get("lang", "te")
            tr = obj.translations.filter(language=lang).first()
            if not tr:
                tr = obj.translations.filter(language="te").first()
            self._cached_translation = tr
        return self._cached_translation.content if self._cached_translation else ""

    def get_summary(self, obj):
        # Reuse cached translation
        if not hasattr(self, '_cached_translation'):
            lang = self.context.get("lang", "te")
            tr = obj.translations.filter(language=lang).first()
            if not tr:
                tr = obj.translations.filter(language="te").first()
            self._cached_translation = tr
        
        if not self._cached_translation:
            return ""
        
        if self._cached_translation.summary:
            return self._cached_translation.summary
            
        from .utils import summary_from_content
        return summary_from_content(self._cached_translation.content)

    def get_media(self, obj):
        """
        Returns media data with presigned URLs generated locally.
        """
        media_links = obj.media_links.all().select_related("media")
        if not media_links:
            return []
            
        from apps.media.utils import get_media_url
        result = []
        for link in media_links:
            media = link.media
            media_data = {
                "media_id": link.media_id,
                "usage": link.usage,
                "position": link.position,
            }

            if media:
                media_data.update({
                    "url": get_media_url(media),
                    "media_type": media.media_type,
                    "content_type": media.content_type,
                })

            result.append(media_data)

        return result
