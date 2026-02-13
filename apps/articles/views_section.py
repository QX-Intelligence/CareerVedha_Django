import json
from typing import List

from django.core.cache import cache
from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Article, ArticleFeature
from .cache import get_articles_cache_version
from .utils import get_article_translation, prepare_article_card, summary_from_content
from .pagination import PublicArticlesPagination


def _exclude_expired(qs):
    t = now()
    return qs.exclude(expires_at__isnull=False, expires_at__lt=t)


def _get_featured_ids(section: str, feature_type: str, limit: int) -> List[int]:
    qs = (
        ArticleFeature.objects.filter(
            section=section,
            feature_type=feature_type,
            is_active=True,
            article__status="PUBLISHED",
            article__noindex=False,
            article__published_at__lte=now(),
        )
        .select_related("article")
        .order_by("rank", "-id")
    )

    ids = []
    for f in qs:
        if f.is_live():
            ids.append(f.article_id)
        if len(ids) >= limit:
            break
    return ids


def _fetch_articles_preserve_order(ids: List[int], lang: str):
    if not ids:
        return []

    qs = Article.objects.filter(
        id__in=ids, 
        status="PUBLISHED", 
        noindex=False, 
        published_at__lte=now()
    ).prefetch_related('translations', 'media_links__media', 'article_categories__category')
    
    qs = _exclude_expired(qs)

    m = {a.id: a for a in qs}
    ordered = []
    for _id in ids:
        if _id in m:
            card = prepare_article_card(m[_id], lang)
            if card:
                ordered.append(card)
    return ordered


class HomeFeed(APIView):
    """
    PUBLIC
    GET /api/articles/home/?lang=te&limit=20&cursor=<cursor>
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        lang = request.GET.get("lang", "te").strip()

        ver = get_articles_cache_version()
        cursor = request.GET.get("cursor")
        cache_key = f"v{ver}:articles:home:{lang}:{cursor}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached), status=200)

        hero_ids = _get_featured_ids(section="", feature_type="HERO", limit=5)
        breaking_ids = _get_featured_ids(section="", feature_type="BREAKING", limit=1)
        top_ids = _get_featured_ids(section="", feature_type="TOP", limit=10)
        must_read_ids = _get_featured_ids(section="", feature_type="MUST_READ", limit=10)

        used = set()
        hero_ids = [i for i in hero_ids if i not in used and not used.add(i)]
        breaking_ids = [i for i in breaking_ids if i not in used and not used.add(i)]
        top_ids = [i for i in top_ids if i not in used and not used.add(i)]
        must_read_ids = [i for i in must_read_ids if i not in used and not used.add(i)]

        hero = _fetch_articles_preserve_order(hero_ids, lang)
        breaking = _fetch_articles_preserve_order(breaking_ids, lang)
        top_stories = _fetch_articles_preserve_order(top_ids, lang)
        must_read = _fetch_articles_preserve_order(must_read_ids, lang)

        qs = Article.objects.filter(
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now()
        ).prefetch_related('translations', 'media_links__media', 'article_categories__category').order_by("-id")
        
        qs = _exclude_expired(qs)

        paginator = PublicArticlesPagination()
        page = paginator.paginate_queryset(qs, request)
        
        results = []
        if page is not None:
            results = [x for x in [prepare_article_card(a, lang) for a in page] if x]
            
        paginated_response = paginator.get_paginated_response(results)

        data = {
            "hero": hero,
            "breaking": breaking,
            "top_stories": top_stories,
            "must_read": must_read,
            "latest": paginated_response.data
        }

        cache.set(cache_key, json.dumps(data, default=str), timeout=60)
        return Response(data, status=status.HTTP_200_OK)


class SectionFeed(APIView):
    """
    PUBLIC
    GET /api/articles/section/<section>/?lang=te&limit=20&cursor=<cursor>
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section):
        lang = request.GET.get("lang", "te").strip()

        ver = get_articles_cache_version()
        cursor = request.GET.get("cursor")
        cache_key = f"v{ver}:articles:section_feed:{section}:{lang}:{cursor}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached), status=200)

        hero_ids = _get_featured_ids(section=section, feature_type="HERO", limit=5)
        breaking_ids = _get_featured_ids(section=section, feature_type="BREAKING", limit=1)
        top_ids = _get_featured_ids(section=section, feature_type="TOP", limit=10)
        must_read_ids = _get_featured_ids(section=section, feature_type="MUST_READ", limit=10)

        used = set()
        hero_ids = [i for i in hero_ids if i not in used and not used.add(i)]
        breaking_ids = [i for i in breaking_ids if i not in used and not used.add(i)]
        top_ids = [i for i in top_ids if i not in used and not used.add(i)]
        must_read_ids = [i for i in must_read_ids if i not in used and not used.add(i)]

        # Fetch latest articles for this section
        qs = Article.objects.filter(
            section=section, 
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now()
        ).prefetch_related('translations', 'media_links__media', 'article_categories__category').order_by("-id")
        
        qs = _exclude_expired(qs)

        paginator = PublicArticlesPagination()
        page = paginator.paginate_queryset(qs, request)
        
        results = []
        if page is not None:
            results = [x for x in [prepare_article_card(a, lang) for a in page] if x]
            
        paginated_response = paginator.get_paginated_response(results)

        data = {
            "section": section,
            "hero": _fetch_articles_preserve_order(hero_ids, lang),
            "breaking": _fetch_articles_preserve_order(breaking_ids, lang),
            "top_stories": _fetch_articles_preserve_order(top_ids, lang),
            "must_read": _fetch_articles_preserve_order(must_read_ids, lang),
            "latest": paginated_response.data
        }

        cache.set(cache_key, json.dumps(data, default=str), timeout=60)
        return Response(data, status=status.HTTP_200_OK)
