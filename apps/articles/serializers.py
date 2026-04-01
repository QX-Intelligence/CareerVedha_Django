from rest_framework import serializers
from .models import Article, ArticleTranslation, ArticleCategory, ArticleMedia, ArticleSection, TopStory, TopStoryMedia
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
    section = serializers.CharField(source='category.section.slug', allow_null=True, required=False)
    slug = serializers.CharField(source='category.slug')
    is_active = serializers.BooleanField(source='category.is_active')
    parent = serializers.SerializerMethodField()
    
    def get_parent(self, obj):
        from .utils import format_category_detail
        parent = obj.category.parent if obj.category else None
        if not parent:
            return None
        return {
            "id": parent.id,
            "name": parent.name,
            "slug": parent.slug
        }

    class Meta:
        model = ArticleCategory
        fields = ("id", "name", "section", "slug", "is_active", "parent")


class ArticleSerializer(serializers.ModelSerializer):
    translations = ArticleTranslationSerializer(many=True, required=False)
    media_links = ArticleMediaSerializer(many=True, read_only=True)
    title = serializers.CharField(read_only=True)

    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    categories = serializers.SerializerMethodField(read_only=True)
    
    additional_sections = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    sections = serializers.SerializerMethodField(read_only=True)
    
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

            "youtube_url",
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
            "is_top_story",
            "banner_file",
            "banner_media_id",
            "main_file",
            "main_media_id",
            "additional_sections",
            "sections",
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
            "sections",
        )

    def get_categories(self, obj):
        from .utils import format_category_detail
        # Use prefetched article_categories
        return [
            format_category_detail(ac.category) 
            for ac in obj.article_categories.all()
            if ac.category
        ]

    def to_internal_value(self, data):
        # 🧪 Robust parsing for Multipart/Form-Data (handles stringified lists like "[1,2]" or "1,2")
        # We catch these before they reach the ListField validation
        mutable_data = data.copy() if hasattr(data, 'copy') else data
        
        # 📂 Handle category_ids stringified list
        if 'category_ids' in mutable_data:
            val = mutable_data.get('category_ids')
            if isinstance(val, str) and (val.startswith('[') or ',' in val):
                try:
                    import json
                    parsed = json.loads(val) if val.startswith('[') else val.split(',')
                    mutable_data['category_ids'] = [int(x) for x in parsed if str(x).strip()]
                except (ValueError, json.JSONDecodeError):
                    pass
        
        # 📂 Handle additional_sections stringified list
        if 'additional_sections' in mutable_data:
            val = mutable_data.get('additional_sections')
            if isinstance(val, str) and (val.startswith('[') or ',' in val):
                try:
                    import json
                    parsed = json.loads(val) if val.startswith('[') else val.split(',')
                    mutable_data['additional_sections'] = [str(x).strip() for x in parsed if str(x).strip()]
                except (ValueError, json.JSONDecodeError):
                    pass

        return super().to_internal_value(mutable_data)

    def to_representation(self, instance):
        # We manually inject category_ids since it's a many-to-many through record
        data = super().to_representation(instance)
        # Ensure category_ids is always a list of integers
        data['category_ids'] = list(instance.article_categories.values_list('category_id', flat=True))
        return data

    def get_title(self, obj):
        return obj.title

    def get_sections(self, obj):
        # Return list including primary and secondary sections
        secs = [obj.section]
        if hasattr(obj, 'article_sections'):
            secs.extend(obj.article_sections.values_list('section', flat=True).distinct())
        return list(set(filter(None, secs)))

    def validate_translations(self, value):
        langs = [t.get("language") for t in value]
        if len(langs) != len(set(langs)):
            raise serializers.ValidationError("Duplicate translation language found")
        return value

    def validate(self, data):
        # Only require translations on creation
        # For updates, we allow empty data if fields aren't being changed
        is_update = self.instance is not None
        
        has_eng = data.get("eng_title") or data.get("eng_content")
        has_tel = data.get("tel_title") or data.get("tel_content")
        has_nest = bool(data.get("translations"))
        
        if not is_update and not (has_eng or has_tel or has_nest):
            raise serializers.ValidationError("At least one language translation (Telugu or English) must be provided.")
            
        return data

    def _sync_translations(self, article, data):
        """Helper to sync nested and direct language fields."""
        # 1. Nested translations
        translations_list = data.pop("translations", [])
        for tr in translations_list:
            lang = tr.pop("language", None)
            if lang:
                ArticleTranslation.objects.update_or_create(
                    article=article, language=lang, defaults=tr
                )
        
        # 2. Direct English fields
        eng_title = data.pop("eng_title", "").strip()
        eng_content = data.pop("eng_content", "").strip()
        eng_summary = data.pop("eng_summary", "").strip()
        if eng_title or eng_content or eng_summary:
            ArticleTranslation.objects.update_or_create(
                article=article, language="en",
                defaults={"title": eng_title, "content": eng_content, "summary": eng_summary}
            )
            
        # 3. Direct Telugu fields
        tel_title = data.pop("tel_title", "").strip()
        tel_content = data.pop("tel_content", "").strip()
        tel_summary = data.pop("tel_summary", "").strip()
        if tel_title or tel_content or tel_summary:
            ArticleTranslation.objects.update_or_create(
                article=article, language="te",
                defaults={"title": tel_title, "content": tel_content, "summary": tel_summary}
            )

    def create(self, validated_data):
        # Extract fields handled in _sync_translations and other special fields
        category_ids = validated_data.pop("category_ids", [])
        additional_sections = validated_data.pop("additional_sections", [])
        banner_file = validated_data.pop("banner_file", None)
        banner_media_id = validated_data.pop("banner_media_id", None)
        main_file = validated_data.pop("main_file", None)
        main_media_id = validated_data.pop("main_media_id", None)

        # Separate language data for helper
        lang_data = {
            "translations": validated_data.pop("translations", []),
            "eng_title": validated_data.pop("eng_title", ""),
            "eng_content": validated_data.pop("eng_content", ""),
            "eng_summary": validated_data.pop("eng_summary", ""),
            "tel_title": validated_data.pop("tel_title", ""),
            "tel_content": validated_data.pop("tel_content", ""),
            "tel_summary": validated_data.pop("tel_summary", ""),
        }

        article = Article.objects.create(**validated_data)
        self._sync_translations(article, lang_data)
        
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


        for cid in category_ids:
            ArticleCategory.objects.get_or_create(article=article, category_id=cid)

        for sec in additional_sections:
            if sec and sec != article.section:
                ArticleSection.objects.get_or_create(article=article, section=sec)

        return article

    def update(self, instance, validated_data):
        # Extract fields for helper and other special fields
        category_ids = validated_data.pop("category_ids", None)
        additional_sections = validated_data.pop("additional_sections", None)
        banner_file = validated_data.pop("banner_file", None)
        banner_media_id = validated_data.pop("banner_media_id", None)
        main_file = validated_data.pop("main_file", None)
        main_media_id = validated_data.pop("main_media_id", None)

        lang_data = {
            "translations": validated_data.pop("translations", []),
            "eng_title": validated_data.pop("eng_title", ""),
            "eng_content": validated_data.pop("eng_content", ""),
            "eng_summary": validated_data.pop("eng_summary", ""),
            "tel_title": validated_data.pop("tel_title", ""),
            "tel_content": validated_data.pop("tel_content", ""),
            "tel_summary": validated_data.pop("tel_summary", ""),
        }

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        self._sync_translations(instance, lang_data)

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

        # Sync sections if provided
        if additional_sections is not None:
            # Filter out primary section if accidentally included
            additional_sections = [s for s in additional_sections if s and s != instance.section]
            ArticleSection.objects.filter(article=instance).exclude(section__in=additional_sections).delete()
            for sec in additional_sections:
                ArticleSection.objects.get_or_create(article=instance, section=sec)

        return instance


class PublicArticleDetailSerializer(serializers.ModelSerializer):
    media = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()

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
            "youtube_url",
            "noindex",
            "og_title",
            "og_description",
            "og_image_url",
            "published_at",
            "created_at",
            "updated_at",
            "media",
            "categories",
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

    def get_categories(self, obj):
        # Fetch categories linked to this article
        from .utils import format_category_detail
        categories = obj.article_categories.all()
        return [
            format_category_detail(ac.category)
            for ac in categories
        ]

class TopStoryMediaSerializer(serializers.ModelSerializer):
    media_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TopStoryMedia
        fields = ("id", "media_details", "position")

    def get_media_details(self, obj):
        if obj.media:
            from apps.media.utils import get_media_url
            return {
                "id": obj.media.id,
                "title": obj.media.title,
                "url": get_media_url(obj.media),
                "media_type": obj.media.media_type,
                "content_type": obj.media.content_type
            }
        return None

class TopStorySerializer(serializers.ModelSerializer):
    media = TopStoryMediaSerializer(source="media_links", many=True, read_only=True)
    media_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    category_detail = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = TopStory
        fields = [
            "id", "title_en", "title_te", "description_en", "description_te",
            "category", "category_detail", "rank", "publish_date", "expiry_date", 
            "is_top_story", "views", "created_at", "updated_at", "media", "media_ids"
        ]
        read_only_fields = ["id", "views", "created_at", "updated_at"]

    def get_category_detail(self, obj):
        from .utils import format_category_detail
        return format_category_detail(obj.category)

    def create(self, validated_data):
        media_ids = validated_data.pop("media_ids", [])
        top_story = super().create(validated_data)
        
        for idx, media_id in enumerate(media_ids):
            try:
                asset = MediaAsset.objects.get(id=media_id)
                TopStoryMedia.objects.create(
                    top_story=top_story,
                    media=asset,
                    position=idx
                )
            except MediaAsset.DoesNotExist:
                pass
                
        return top_story

    def update(self, instance, validated_data):
        media_ids = validated_data.pop("media_ids", None)
        top_story = super().update(instance, validated_data)
        
        if media_ids is not None:
            TopStoryMedia.objects.filter(top_story=top_story).delete()
            for idx, media_id in enumerate(media_ids):
                try:
                    asset = MediaAsset.objects.get(id=media_id)
                    TopStoryMedia.objects.create(
                        top_story=top_story,
                        media=asset,
                        position=idx
                    )
                except MediaAsset.DoesNotExist:
                    pass

        return top_story
