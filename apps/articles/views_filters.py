from django.utils.timezone import now
from django.db.models import Count, Q
import django.utils.timezone as timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import ArticleCategory, Article
from apps.taxonomy.models import Category


class ArticleFilters(APIView):
    """
    PUBLIC
    GET /api/articles/filters/?section=academics&category=...&sub_category=...&segment=...&lang=te
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        section = request.GET.get("section")
        category_slug = request.GET.get("category")
        sub_category_slug = request.GET.get("sub_category")
        segment_slug = request.GET.get("segment")
        lang = request.GET.get("lang", "te").strip()

        # Base queryset: only published, visible, non-expired articles
        qs = Article.objects.prefetch_related(
            'translations', 
            'article_categories__category',
            'media_links__media'
        ).filter(
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now()
        )
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        # Filter by section
        if section:
            qs = qs.filter(Q(section__iexact=section) | Q(article_sections__section__iexact=section)).distinct()

        # Hierarchical Category Filtering
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

        if target_category:
            # Get all child categories recursively
            def get_ids(cat):
                ids = [cat.id]
                for child in cat.children.all():
                    ids.extend(get_ids(child))
                return ids
            
            category_ids = get_ids(target_category)
            qs = qs.filter(article_categories__category_id__in=category_ids).distinct()

        total = qs.count()

        # Top categories within the current filtered set
        category_counts = (
            ArticleCategory.objects.filter(article__in=qs, category__is_active=True)
            .values("category_id", "category__name", "category__slug")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Get latest 10 articles for this filter
        from .utils import prepare_article_card
        latest_articles = [x for x in [prepare_article_card(a, lang) for a in qs.order_by("-published_at")[:10]] if x]

        return Response(
            {
                "section": section or "",
                "total_published": total,
                "top_categories": list(category_counts),
                "articles": latest_articles
            },
            status=status.HTTP_200_OK,
        )


class TaxonomyArticleFilters(APIView):
    """
    PUBLIC
    GET /api/articles/taxonomy-filters/?section=...&category=...&sub_category=...&segment=...&lang=te
    
    Dedicated endpoint for hierarchical taxonomy filtering.
    Returns the latest 10 articles for the selected level.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        section = request.GET.get("section")
        category_slug = request.GET.get("category")
        sub_category_slug = request.GET.get("sub_category")
        segment_slug = request.GET.get("segment")
        lang = request.GET.get("lang", "te").strip()

        # 1. Base query
        qs = Article.objects.prefetch_related(
            'translations', 
            'article_categories__category',
            'media_links__media'
        ).filter(
            status="PUBLISHED", 
            noindex=False, 
            published_at__lte=now()
        )
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))

        if section:
            qs = qs.filter(Q(section__iexact=section) | Q(article_sections__section__iexact=section)).distinct()

        # 2. Hierarchical Traversal
        target_category = None
        if category_slug:
            cat_query = Q(slug=category_slug, parent__isnull=True)
            if section:
                cat_query &= Q(section__slug__iexact=section)
            target_category = Category.objects.filter(cat_query).first()
            
            if target_category and sub_category_slug:
                sub_cat = Category.objects.filter(slug=sub_category_slug, parent=target_category).first()
                if sub_cat:
                    target_category = sub_cat
                    if segment_slug:
                        seg_cat = Category.objects.filter(slug=segment_slug, parent=target_category).first()
                        if seg_cat:
                            target_category = seg_cat

        # 3. Apply Filter
        if target_category:
            def get_ids(cat):
                ids = [cat.id]
                for child in cat.children.all():
                    ids.extend(get_ids(child))
                return ids
            category_ids = get_ids(target_category)
            qs = qs.filter(article_categories__category_id__in=category_ids).distinct()
        elif category_slug:
            # If slug was provided but not found
            return Response({"results": []}, status=200)

        # 4. Results
        from .utils import prepare_article_card
        articles = [x for x in [prepare_article_card(a, lang) for a in qs.order_by("-published_at")[:10]] if x]
        
        return Response({
            "category": {
                "id": target_category.id if target_category else None,
                "name": target_category.name if target_category else None,
                "slug": target_category.slug if target_category else None,
            },
            "results": articles
        }, status=status.HTTP_200_OK)
