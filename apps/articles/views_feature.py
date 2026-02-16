from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from apps.common.jwt import get_user_from_jwt
from apps.common.permissions import require_min_role

from .models import Article, ArticleFeature
from .pagination import ArticleFeatureCursorPagination
from .cache import bump_articles_cache_version

ALLOWED_FEATURES = ["HERO", "TOP", "BREAKING", "EDITOR_PICK"]
FEATURE_LIMITS = {
    "HERO": 5,
    "TOP": 10,
    "BREAKING": 1,
    "EDITOR_PICK": 10,
}

class GetFeatures(APIView):
    """
    GET /api/cms/articles/features/?feature_type=TOP&section=academics&limit=50
    Get list of pinned/featured articles
    """

    def get(self, request):
        #user = get_user_from_jwt(request)
        #require_min_role(user, "EDITOR")
        feature_type = (request.GET.get("feature_type") or "").strip().upper()
        section = (request.GET.get("section") or "").strip()
        lang = (request.GET.get("lang") or "").strip().lower()

        if feature_type not in ALLOWED_FEATURES:
            raise ValidationError({"feature_type": f"Invalid. Allowed: {ALLOWED_FEATURES}"})

        # Count total features in database for this type
        total_count = ArticleFeature.objects.filter(feature_type=feature_type).count()

        # Build query
        qs = ArticleFeature.objects.filter(feature_type=feature_type)
        
        # If section is provided, filter by it.
        if section:
            from django.db.models import Q
            qs = qs.filter(Q(section=section) | Q(section="") | Q(section__isnull=True))
            # Strict filter: only show articles belonging to this section & global pins that match
            qs = qs.filter(article__section__iexact=section)
        
        if lang: 
            qs = qs.filter(article__translations__language=lang)

        # Filter to only PUBLISHED articles and order
        qs = qs.filter(article__status="PUBLISHED").select_related("article").prefetch_related("article__translations").order_by("rank", "-id").distinct()

        paginator = ArticleFeatureCursorPagination()
        page = paginator.paginate_queryset(qs, request)

        features = []
        if page is not None:
            for f in page:
                article = f.article
                
                # Get title based on requested language or default
                article_title = "Untitled"
                if lang:
                    trans = next((t for t in article.translations.all() if t.language == lang), None)
                    if trans:
                        article_title = trans.title
                else:
                    # Fallback to prioritized title (English -> Telugu -> First)
                    article_title = article.prioritized_title or "Untitled"
                
                features.append({
                    "feature_id": f.id,
                    "article_id": article.id,
                    "article_slug": article.slug,
                    "article_section": article.section,  # Added article source section  
                    "article_title": article_title,
                    "article_status": article.status,
                    "section": f.section or "",
                    "rank": f.rank,
                    "is_active": f.is_active,
                    "is_live": f.is_live(),
                    "created_at": f.start_at.isoformat() if f.start_at else None,
                    "ended_at": f.end_at.isoformat() if f.end_at else None,
                })

            response = paginator.get_paginated_response(features)
            # Add extra metadata to response data
            response.data.update({
                "feature_type": feature_type,
                "section": section or "",
                "total_for_type": total_count,
            })
            return response

        return Response(
            {
                "feature_type": feature_type,
                "section": section or "",
                "total_for_type": total_count,
                "results": [],
                "next_cursor": None,
                "has_next": False
            },
            status=200,
        )


class PinFeature(APIView):
    """
    POST /api/cms/articles/<id>/feature/
    """

    def post(self, request, article_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

        article = get_object_or_404(Article, id=article_id)

        if article.status != "PUBLISHED":
            raise ValidationError("Only PUBLISHED articles can be featured")

        feature_type = (request.data.get("feature_type") or "").strip().upper()
        section = (request.data.get("section") or "").strip()

        if feature_type not in ALLOWED_FEATURES:
            raise ValidationError({"feature_type": f"Invalid. Allowed {ALLOWED_FEATURES}"})

        if feature_type == "BREAKING":
            rank = 0
        else:
            rank = int(request.data.get("rank", 1))
            if rank < 1:
                rank = 1

        feature, _ = ArticleFeature.objects.update_or_create(
            article=article,
            feature_type=feature_type,
            section=section,
            defaults={"rank": rank, "is_active": True},
        )

        # enforce limits
        limit = FEATURE_LIMITS[feature_type]
        live_qs = ArticleFeature.objects.filter(
            feature_type=feature_type,
            section=section,
            is_active=True,
        ).order_by("rank", "-id")

        if live_qs.count() > limit:
            extra = live_qs[limit:]
            extra.update(is_active=False, end_at=now())

        bump_articles_cache_version()
        return Response(
            {
                "status": "featured",
                "feature_id": feature.id,
                "feature_type": feature.feature_type,
                "section": feature.section,
                "rank": feature.rank,
            },
            status=200,
        )


class UnpinFeature(APIView):
    """
    DELETE /api/cms/articles/<id>/feature/remove/?feature_type=TOP&section=academics
    """

    def delete(self, request, article_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

        feature_type = (request.GET.get("feature_type") or "").strip().upper()
        section = (request.GET.get("section") or "").strip()

        if feature_type not in ALLOWED_FEATURES:
            raise ValidationError({"feature_type": "Invalid feature_type"})

        qs = ArticleFeature.objects.filter(
            article_id=article_id,
            feature_type=feature_type,
            section=section,
        )

        deleted, _ = qs.delete()
        bump_articles_cache_version()
        return Response({"status": "unfeatured", "deleted": deleted}, status=200)
