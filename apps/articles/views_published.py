import json
from django.core.cache import cache
from django.utils.timezone import now
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Article, ArticleCategory
from .cache import get_articles_cache_version
from .pagination import PublicArticlesPagination
from apps.taxonomy.models import Category


class PublishedArticlesList(APIView):
    """
    PUBLIC
    GET /api/articles/published/?section=academics&category=intermediate&limit=10&cursor=<cursor>
    
    Filters:
    - section: Filter by article section (e.g., 'academics', 'exams', 'news')
    - category: Filter by category slug. Can be hierarchical (e.g., 'intermediate' under 'academics' section)
    
    Returns published articles with cursor-based pagination.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        section = request.GET.get("section")
        category_slug = request.GET.get("category")
        sub_category_slug = request.GET.get("sub_category")
        segment_slug = request.GET.get("segment")
        cursor = request.GET.get("cursor") 

        # Build cache key including new filters and language
        lang = request.GET.get("lang", "te").strip().lower()
        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:published:{section}:{lang}:{category_slug}:{sub_category_slug}:{segment_slug}:{cursor}"
        
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # Base queryset: only published, visible, non-expired articles
        qs = Article.objects.prefetch_related(
            'translations', 
            'article_categories__category',
            'media_links__media'
        ).filter(
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now(),
            translations__language=lang
        ).distinct()
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        # Filter by section
        if section:
            qs = qs.filter(Q(section__iexact=section) | Q(article_sections__section__iexact=section)).distinct()

        # Filter by category (hierarchical support)
        target_category = None
        if category_slug:
            # 1. Find root level category
            cat_query = Q(slug=category_slug, parent__isnull=True)
            if section:
                cat_query &= Q(section__slug__iexact=section)
            
            target_category = Category.objects.filter(cat_query).first()
            
            # 2. Traverse to sub-category if provided
            if target_category and sub_category_slug:
                sub_cat = Category.objects.filter(slug=sub_category_slug, parent=target_category).first()
                if sub_cat:
                    target_category = sub_cat
                    # 3. Traverse to segment if provided
                    if segment_slug:
                        seg_cat = Category.objects.filter(slug=segment_slug, parent=target_category).first()
                        if seg_cat:
                            target_category = seg_cat

        if category_slug and not target_category:
            # If category parameters were provided but no matching category found, return empty
            return Response({
                "results": [],
                "next_cursor": None,
                "has_next": False,
                "limit": PublicArticlesPagination.page_size
            }, status=200)

        if target_category:
            # Get all child categories recursively
            category_ids = self._get_category_tree_ids(target_category)
            # Filter articles that have any of these categories
            qs = qs.filter(article_categories__category_id__in=category_ids).distinct()

        # Apply pagination
        paginator = PublicArticlesPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            from .utils import prepare_article_card
            results = [x for x in [prepare_article_card(a, lang, strict=True) for a in page] if x]

            response = paginator.get_paginated_response(results)
            cache.set(cache_key, json.dumps(response.data, default=str), timeout=300)
            return response

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)

    def _get_category_tree_ids(self, category):
        """
        Recursively get all category IDs including the parent and all children.
        """
        ids = [category.id]
        children = Category.objects.filter(parent=category)
        for child in children:
            ids.extend(self._get_category_tree_ids(child))
        return ids

class RelatedArticlesView(APIView):
    """
    PUBLIC
    GET /api/articles/<section>/<slug>/related/?lang=te
    
    Returns articles sharing categories or tags with the source article.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, section, slug):
        lang = request.GET.get("lang", "te").strip().lower()

        # Check cache
        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:related:{section}:{slug}:{lang}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # 1. Get source article
        source = Article.objects.filter(section=section, slug=slug).first()
        if not source:
            return Response({"results": []})

        # 2. Get categories and tags
        category_ids = list(source.article_categories.values_list('category_id', flat=True))
        tags = source.tags or []

        # 3. Build related articles query
        # Must be PUBLISHED, non-expired, and NOT the source article
        qs = Article.objects.prefetch_related(
            'translations', 
            'article_categories__category',
            'media_links__media'
        ).filter(
            status="PUBLISHED",
            noindex=False,
            published_at__lte=now(),
            translations__language=lang
        ).distinct().exclude(id=source.id)
        
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        # Match by category OR tags
        match_q = Q()
        if category_ids:
            match_q |= Q(article_categories__category_id__in=category_ids)
        
        if tags:
            # Match if any of the source tags are present in the target tags list
            tag_q = Q()
            for tag in tags:
                tag_q |= Q(tags__contains=tag)
            match_q |= tag_q

        if not category_ids and not tags:
             # Fallback: latest in same section
             qs = qs.filter(section=section)
        else:
             qs = qs.filter(match_q).distinct()

        # 4. Final ordering and limit
        qs = qs.order_by("-published_at")[:5]

        from .utils import prepare_article_card
        results = [x for x in [prepare_article_card(a, lang, strict=True) for a in qs] if x]

        data = {"results": results}
        cache.set(cache_key, json.dumps(data, default=str), timeout=300)
        return Response(data)

class TopStoriesView(APIView):
    """
    PUBLIC
    GET /api/articles/top-stories/?lang=te
    
    Returns the latest 5 top stories (is_top_story=True),
    excluding expired ones.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        limit = 5
        lang = request.GET.get("lang", "te").strip().lower()

        # Build cache key
        ver = get_articles_cache_version()
        cache_key = f"v{ver}:articles:top_stories:{lang}"
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # Base queryset: is_top_story=True, PUBLISHED, non-expired
        qs = Article.objects.prefetch_related(
            'translations', 
            'article_categories__category',
            'media_links__media'
        ).filter(
            is_top_story=True,
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now(),
            translations__language=lang
        ).distinct()
        # Expiry filter
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        # Order by latest published
        qs = qs.order_by("-published_at")[:limit]

        from .utils import prepare_article_card
        results = [x for x in [prepare_article_card(a, lang, strict=True) for a in qs] if x]

        data = {"results": results}
        cache.set(cache_key, json.dumps(data, default=str), timeout=300)
        return Response(data)
