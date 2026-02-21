from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .pagination import ArticleCursorPagination, ArticleRevisionCursorPagination, ArticleSearchPagination
from apps.common.jwt import get_user_from_jwt
from apps.common.permissions import require_min_role, get_role_level, _normalize_role
from .notification_service import notification_service

from .models import (
    Article,
    ArticleTranslation,
    ArticleCategory,
    ArticleRevision
)
from .serializers import ArticleSerializer
from .cache import bump_articles_cache_version


def get_target_receiver_role(actor_role):
    """
    Hierarchical mapping of actor role to next-level required receiver role.
    - Contributor -> Editor
    - Editor -> Publisher
    - Publisher -> Admin (Admins & Super Admins)
    - Admin -> Super Admin (Only Super Admins)
    """
    role = _normalize_role(actor_role)
    mapping = {
        "CONTRIBUTOR": "EDITOR",
        "EDITOR": "PUBLISHER",
        "PUBLISHER": "ADMIN",
        "ADMIN": "SUPER_ADMIN",
        "SUPER_ADMIN": "SUPER_ADMIN"
    }
    # Default to EDITOR if role is unknown or contributor, 
    # but for ADMIN it MUST be SUPER_ADMIN
    return mapping.get(role, "EDITOR")


def _get_spring_boot_token(request):
    """Extract Bearer token from Authorization header."""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        return auth_header.replace('Bearer ', '').strip()
    return auth_header.strip() if auth_header else None


class CreateArticle(APIView):
    """
    POST /api/cms/articles/
    role: CONTRIBUTOR+    
    Request Body Fields:
    - slug: Article URL slug (required)
    - section: Article section (required)
    - summary: Article summary (optional)
    - translations: [
        {
            "language": "en",
            "title": "English Title",
            "content": "<p>English content here</p>"
        },
        {
            "language": "te",
            "title": "తెలుగు శీర్షిక",
            "content": "<p>తెలుగు కంటెంట్ ఇక్కడ</p>"
        }
      ]
    - category_ids: [1, 2, 3] (optional)
    - tags: ["tech", "news"] (optional)
    - keywords: ["technology", "article"] (optional)
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "CONTRIBUTOR")
        request.cms_user = user

    def post(self, request):
        user = request.cms_user

        from django.db import transaction
        
        try:
            with transaction.atomic():
                serializer = ArticleSerializer(data=request.data)
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                article = serializer.save(
                    created_by=str(user["user_id"]),
                    updated_by=str(user["user_id"])
                )
                
                # ------------------------------------------------------------------
                # DIRECT PUBLISH / SCHEDULE (ADMIN/SUPER_ADMIN ONLY)
                # ------------------------------------------------------------------
                requested_status = request.data.get("status")
                scheduled_at_str = request.data.get("scheduled_at")
                
                if (requested_status == "PUBLISHED" or scheduled_at_str) and get_role_level(user["role"]) >= get_role_level("PUBLISHER"):
                    if not article.translations.exists():
                        # If no translations exist, we can't publish
                        # Transaction will roll back the article creation
                        return Response({"error": "At least 1 translation required to publish"}, status=status.HTTP_400_BAD_REQUEST)

                    from django.utils.timezone import now
                    from zoneinfo import ZoneInfo
                    from dateutil import parser
                    
                    published_at = now()
                    if scheduled_at_str:
                        try:
                            # Robust parsing using dateutil
                            parsed_date = parser.parse(str(scheduled_at_str))
                            
                            # With USE_TZ=False, we store naive datetimes.
                            if parsed_date.tzinfo is not None:
                                published_at = parsed_date.astimezone(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
                            else:
                                published_at = parsed_date
                        except (ValueError, TypeError):
                            return Response({"error": "Invalid date format for scheduled_at"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    article.status = "PUBLISHED" if published_at <= now() else "SCHEDULED"
                    article.noindex = False
                    article.published_at = published_at
                    article.save(update_fields=["status", "noindex", "published_at"])
                    
                    # Notification
                    notification_service.notify_on_publish(
                        article_id=article.id,
                        article_title=article.translations.first().title,
                        publisher_id=article.updated_by,
                        receiver_role=get_target_receiver_role(user["role"]),
                        spring_boot_token=_get_spring_boot_token(request)
                    )
                else:
                    # Regular Create Notification
                    notification_service.notify_on_create(
                        article_id=article.id,
                        article_title=article.slug,
                        contributor_id=article.created_by,
                        receiver_role=get_target_receiver_role(user["role"]),
                        spring_boot_token=_get_spring_boot_token(request)
                    )
                
                article.save(update_fields=["created_by", "updated_by"])
                bump_articles_cache_version()
                return Response(ArticleSerializer(article).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Catch unexpected errors to avoid leaving half-created articles if transaction failed
            # Though transaction.atomic handles the rollback, this provides a cleaner response
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class ArticleReject(APIView):
    
    """PATCH /api/cms/articles/<id>/reject/
    role: EDITOR+
    """
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")
        request.cms_user = user

    def patch(self, request, article_id):
        user = request.cms_user

        article = get_object_or_404(Article, id=article_id)

        reason = request.data.get("reason", "")

        article.status = "REJECTED"
        article.updated_by = str(user["user_id"])
        article.save(update_fields=["status", "updated_by"])

        # Send notification about article rejection
        notification_service.notify_on_reject(
            article_id=article.id,
            article_title=article.translations.first().title if article.translations.exists() else f"Article {article.id}",
            editor_id=article.updated_by,
            reason=reason,
            receiver_role=get_target_receiver_role(user["role"]),
            spring_boot_token=_get_spring_boot_token(request)
        )


# ------------------------
# CMS: Add/update translation (with revision)
# ------------------------
class AddOrUpdateTranslation(APIView):
    """
    POST /api/cms/articles/<id>/translation/
    role: EDITOR+
    """

    def post(self, request, article_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

        article = get_object_or_404(Article, id=article_id)

        language = request.data.get("language")
        title = request.data.get("title")
        content = request.data.get("content")
        summary = request.data.get("summary", "")
        note = request.data.get("note", "")

        if not language or not title or (not content and not summary):
            return Response({"error": "language, title, content/summary required"}, status=400)

        ArticleTranslation.objects.update_or_create(
            article=article,
            language=language,
            defaults={"title": title, "content": content, "summary": summary},
        )

        ArticleRevision.objects.create(
            article=article,
            language=language,
            title=title,
            content=content,
            summary=summary,
            editor_user_id=str(user["user_id"]),
            note=note,
        )

        article.updated_by = str(user["user_id"])
        article.save(update_fields=["updated_by"])

        # Send notification about article update
        notification_service.notify_on_update(
            article_id=article.id,
            article_title=title,
            editor_id=article.updated_by,
            receiver_role=get_target_receiver_role(user["role"]),
            spring_boot_token=_get_spring_boot_token(request)
        )

        bump_articles_cache_version()
        return Response({"status": "saved"}, status=status.HTTP_201_CREATED)


# ------------------------
# CMS: Assign categories
# ------------------------
class AssignCategories(APIView):
    """
    POST /api/cms/articles/<id>/categories/
    role: EDITOR+
    body: { "category_ids": [1,2,3] }
    """
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "CONTRIBUTOR")
        request.cms_user = user

    def post(self, request, article_id):
        user = request.cms_user

        article = get_object_or_404(Article, id=article_id)
        category_ids = request.data.get("category_ids", [])

        if not isinstance(category_ids, list):
            return Response({"error": "category_ids must be a list"}, status=400)

        ArticleCategory.objects.filter(article=article).delete()

        for cid in category_ids:
            ArticleCategory.objects.create(article=article, category_id=cid)

        article.updated_by = str(user["user_id"])
        article.save(update_fields=["updated_by"])

        bump_articles_cache_version()
        return Response({"status": "categories updated"}, status=200)


# ------------------------
# CMS: Move to review (strict rules)
# ------------------------
class MoveToReview(APIView):
    """
    PATCH /api/cms/articles/<id>/review/
    role: EDITOR+
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")
        request.cms_user = user

    def patch(self, request, article_id):
        user = request.cms_user

        article = get_object_or_404(Article, id=article_id)

        # HARD RULES (Sakshi-style)
        if not article.translations.filter(language="te").exists():
            return Response({"error": "Telugu translation (te) required"}, status=400)

        if not article.article_categories.exists():
            return Response({"error": "At least 1 category required"}, status=400)

        article.status = "REVIEW"
        article.updated_by = str(user["user_id"])
        article.save(update_fields=["status", "updated_by"])

        # Send notification to editors about article in review
        notification_service.notify_on_review(
            article_id=article.id,
            article_title=article.translations.first().title if article.translations.exists() else f"Article {article.id}",
            contributor_id=article.created_by,
            receiver_role=get_target_receiver_role(user["role"]),
            spring_boot_token=_get_spring_boot_token(request)
        )

        bump_articles_cache_version()
        return Response({"status": "review"}, status=200)


# ------------------------
# CMS: Publish (strict)
# ------------------------
class PublishArticle(APIView):
    """
    PATCH /api/cms/articles/<id>/publish/
    role: PUBLISHER+
    """

    def patch(self, request, article_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

        article = get_object_or_404(Article, id=article_id)

        if article.status != "REVIEW":
            return Response({"error": "Must be REVIEW before publish"}, status=400)

        if not article.translations.filter(language="te").exists():
            return Response({"error": "Telugu translation (te) required"}, status=400)

        article.status = "PUBLISHED"
        article.noindex = False
        article.published_at = now()
        article.updated_by = str(user["user_id"])
        article.save(update_fields=["status", "noindex", "published_at", "updated_by"])

        # Send notification to admins about published article
        notification_service.notify_on_publish(
            article_id=article.id,
            article_title=article.translations.first().title if article.translations.exists() else f"Article {article.id}",
            publisher_id=article.updated_by,
            receiver_role=get_target_receiver_role(user["role"]),
            spring_boot_token=_get_spring_boot_token(request)
        )

        bump_articles_cache_version()
        return Response({"status": "published"}, status=200)


class AdminArticleDirectPublish(APIView):
    """
    PATCH /api/cms/articles/<id>/direct-publish/
    role: ADMIN+
    body: { "scheduled_at": "2023-10-27T10:00:00" } (optional)
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "ADMIN")
        request.cms_user = user

    def patch(self, request, article_id):
        user = request.cms_user

        article = get_object_or_404(Article, id=article_id)
        
        if not article.translations.exists():
             return Response({"error": "At least 1 translation required to publish"}, status=400)
             
        # Schedule logic
        scheduled_at_str = request.data.get("scheduled_at")
        published_at = now()
        
        if scheduled_at_str:
            from zoneinfo import ZoneInfo
            from dateutil import parser
            try:
                # Robust parsing using dateutil (handles "2026-02-4T13:10:00")
                parsed_date = parser.parse(str(scheduled_at_str))
                
                # With USE_TZ=False, we store naive datetimes.
                # If the input has a timezone, we convert it to naive IST.
                # If it's already naive, we assume it's IST.
                if parsed_date.tzinfo is not None:
                    published_at = parsed_date.astimezone(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
                else:
                    published_at = parsed_date
            except (ValueError, TypeError):
                return Response({"error": "Invalid date format for scheduled_at"}, status=400)

        article.status = "PUBLISHED" if published_at <= now() else "SCHEDULED"
        article.noindex = False
        article.published_at = published_at
        article.updated_by = str(user["user_id"])
        
        # Save updates
        article.save(update_fields=["status", "noindex", "published_at", "updated_by"])

        # Notification (using regular publish notification for now)
        notification_service.notify_on_publish(
            article_id=article.id,
            article_title=article.translations.first().title if article.translations.exists() else f"Article {article.id}",
            publisher_id=article.updated_by,
            receiver_role=get_target_receiver_role(user["role"]),
            spring_boot_token=_get_spring_boot_token(request)
        )

        bump_articles_cache_version()
        
        msg = "published" if published_at <= now() else "scheduled"
        return Response({"status": msg, "published_at": article.published_at}, status=200)


# ------------------------
# CMS: Deactivate
# ------------------------
class DeactivateArticle(APIView):
    """
    PATCH /api/cms/articles/<id>/deactivate/
    role: PUBLISHER+
    """

    def patch(self, request, article_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

        article = get_object_or_404(Article, id=article_id)
        article.status = "INACTIVE"
        article.noindex = True
        article.updated_by = str(user["user_id"])
        article.save(update_fields=["status", "noindex", "updated_by"])
        
        notification_service.notify_on_deactivate(
            article_id=article.id,
            article_title=article.translations.first().title if article.translations.exists() else f"Article {article.id}",
            admin_id=article.updated_by,
            receiver_role=get_target_receiver_role(user["role"]),
            spring_boot_token=_get_spring_boot_token(request)
        )

        bump_articles_cache_version()
        return Response({"status": "inactive"}, status=200)


# ------------------------
# CMS: Activate
# ------------------------
class ActivateArticle(APIView):
    """
    PATCH /api/cms/articles/<id>/activate/
    role: PUBLISHER+
    """

    def patch(self, request, article_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

        article = get_object_or_404(Article, id=article_id)
        article.status = "DRAFT"
        article.noindex = True
        article.updated_by = str(user["user_id"])
        article.save(update_fields=["status", "noindex", "updated_by"])
        
        notification_service.notify_on_activate(
            article_id=article.id,
            article_title=article.translations.first().title if article.translations.exists() else f"Article {article.id}",
            admin_id=article.updated_by,
            receiver_role=get_target_receiver_role(user["role"]),
            spring_boot_token=_get_spring_boot_token(request)
        )

        bump_articles_cache_version()
        return Response({"status": "active"}, status=200)


# ------------------------
# CMS: Admin list
# ------------------------
class AdminArticleList(APIView):
    """
    GET /api/cms/articles/admin/list/  
    role: EDITOR+
    """

    def get(self, request):
        user = get_user_from_jwt(request)
        require_min_role(user, "CONTRIBUTOR")

        # Filters
        section = request.GET.get("section")
        status_filter = request.GET.get("status")
        search_query = request.GET.get("q", "").strip()

        qs = (
            Article.objects
            .prefetch_related(
                'translations',
                'media_links__media',
                'article_categories__category'
            )
            .all()
            .order_by("-created_at", "-id")
        )

        if section:
            qs = qs.filter(section=section)
        
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        if search_query:
            search_filters = Q(translations__title__icontains=search_query) | Q(slug__icontains=search_query) | Q(translations__summary__icontains=search_query)
            if search_query.isdigit():
                search_filters |= Q(id=int(search_query))
            
            qs = qs.filter(search_filters).distinct()

        paginator = ArticleCursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = ArticleSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback for empty list
        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)


# ------------------------
# CMS: Revision list
# ------------------------
class ArticleRevisionList(APIView):
    """
    GET /api/cms/articles/<id>/revisions/?language=te
    role: EDITOR+
    """

    def get(self, request, article_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

        language = request.GET.get("language")
        qs = ArticleRevision.objects.filter(article_id=article_id).order_by("-created_at", "-id")
        if language:
            qs = qs.filter(language=language)

        paginator = ArticleRevisionCursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            results = [
                {
                    "id": r.id,
                    "language": r.language,
                    "title": r.title,
                    "note": r.note,
                    "editor_user_id": r.editor_user_id,
                    "created_at": r.created_at,
                }
                for r in page
            ]
            return paginator.get_paginated_response(results)

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)
        
        
class ArticleDelete(APIView):
    """
    GET /api/cms/articles/<id>/ - Fetch article details with all translations (EDITOR+)
    PATCH /api/cms/articles/<id>/ - Update article details (EDITOR+)
    DELETE /api/cms/articles/<id>/ - Delete article (ADMIN+)
    """

    def get(self, request, article_id):
        """Fetch full article details including translations"""
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

        article = get_object_or_404(
            Article.objects.prefetch_related('translations', 'media_links', 'article_categories__category'), 
            id=article_id
        )
        serializer = ArticleSerializer(article)
        return Response(serializer.data)

    def patch(self, request, article_id):
        """Update article details using serializer logic"""
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

        article = get_object_or_404(Article, id=article_id)
        
        serializer = ArticleSerializer(article, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        article = serializer.save(updated_by=str(user["user_id"]))
        
        bump_articles_cache_version()
        
        return Response(ArticleSerializer(article).data, status=status.HTTP_200_OK)

    def delete(self, request, article_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "ADMIN")

        article = get_object_or_404(Article, id=article_id)
        article_title = article.translations.first().title if article.translations.exists() else f"Article {article.id}"
        
        article.delete()

        notification_service.notify_on_delete(
            article_id=article_id,
            article_title=article_title,
            admin_id=str(user["user_id"]),
            receiver_role=get_target_receiver_role(user["role"]),
            spring_boot_token=_get_spring_boot_token(request)
        )
        bump_articles_cache_version()
        return Response({"status": "deleted"}, status=200)
    
    
class ArticleDeleteMulti(APIView):
    """
    DELETE /api/cms/articles/delete-multi/
    role: ADMIN+
    body: { "article_ids": [1,2,3] }
    """

    def delete(self, request):
        user = get_user_from_jwt(request)
        require_min_role(user, "ADMIN")

        article_ids = request.data.get("article_ids", [])
        if not isinstance(article_ids, list):
            return Response({"error": "article_ids must be a list"}, status=400)

        articles = Article.objects.filter(id__in=article_ids)
        
        for article in articles:
            article_title = article.translations.first().title if article.translations.exists() else f"Article {article.id}"
            article.delete()
            notification_service.notify_on_delete(
                article_id=article.id,
                article_title=article_title,
                admin_id=str(user["user_id"]),
                receiver_role=get_target_receiver_role(user["role"]),
                spring_boot_token=_get_spring_boot_token(request)
            )
    
class ArticleSearch(APIView):
    """
    GET /api/cms/articles/search/?q=keyword
    role: EDITOR+
    Search by article ID or title
    """

    def get(self, request):
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

        query = request.GET.get("q", "").strip()
        if not query:
            return Response({"results": []}, status=200)

        # Search by both ID (if numeric) and title
        search_filters = Q(title__icontains=query)
        
        # If query is numeric, also search by article ID
        if query.isdigit():
            search_filters |= Q(article__id=int(query))

        qs = ArticleTranslation.objects.filter(search_filters).select_related("article").order_by("-article__created_at", "-id")

        paginator = ArticleSearchPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            results = [
                {
                    "article_id": at.article.id,
                    "language": at.language,
                    "title": at.title,
                }
                for at in page
            ]
            return paginator.get_paginated_response(results)

        return Response({
            "next_cursor": None,
            "has_next": False,
            "results": []
        }, status=200)


class AdminArticleSearchSuggestions(APIView):
    """
    CMS: Admin search suggestions
    GET /api/cms/articles/admin/search-suggestions/?q=inter
    role: EDITOR+
    """

    def get(self, request):
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

        q = (request.GET.get("q") or "").strip()
        if not q or len(q) < 2:
            return Response({"suggestions": []}, status=200)

        # Search across all articles (including INACTIVE)
        filters = Q(translations__title__icontains=q) | Q(slug__icontains=q)
        if q.isdigit():
            filters |= Q(id=int(q))

        qs = Article.objects.prefetch_related('translations').filter(filters).distinct().order_by("-id")[:15]

        suggestions = []
        for a in qs:
            suggestions.append({
                "id": a.id,
                "title": a.title,
                "status": a.status,
            })

        return Response({"suggestions": suggestions}, status=200)