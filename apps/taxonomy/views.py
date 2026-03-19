from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache

from .models import Category, Section
from .cache import get_taxonomy_cache_key, TAXONOMY_CACHE_TIMEOUT



class TaxonomyBySection(APIView):
    """
    GET /api/taxonomy/<section>/
    Root-level categories only (PUBLIC)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section):
        cache_key = get_taxonomy_cache_key("TaxonomyBySection", section=section)
        data = cache.get(cache_key)
        
        if data is None:
            categories = Category.objects.filter(
                section__slug=section,
                parent__isnull=True,
                is_active=True
            ).order_by("name", "id")

            data = [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                }
                for c in categories
            ]
            cache.set(cache_key, data, TAXONOMY_CACHE_TIMEOUT)

        return Response(data, status=status.HTTP_200_OK)


class CategoryChildrenBySlug(APIView):
    """
    GET /api/taxonomy/<section>/<slug>/children/
     Only works for ROOT category slug (safe but limited)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section, slug):
        cache_key = get_taxonomy_cache_key("CategoryChildrenBySlug", section=section, slug=slug)
        data = cache.get(cache_key)
        
        if data is None:
            parent = Category.objects.filter(
                section__slug=section,
                slug=slug,
                parent__isnull=True,
                is_active=True,
            ).first()

            if not parent:
                return Response(
                    {"error": "Category not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            children = parent.children.filter(is_active=True).order_by("name", "id")

            data = [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "parent_id": parent.id,
                }
                for c in children
            ]
            cache.set(cache_key, data, TAXONOMY_CACHE_TIMEOUT)

        return Response(data, status=status.HTTP_200_OK)


class CategoryChildrenById(APIView):
    """
    BEST API - Get children by parent_id (PUBLIC)
    GET /api/taxonomy/<section>/children/?parent_id=12
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section):
        parent_id = request.GET.get("parent_id")

        if not parent_id:
            return Response(
                {"error": "parent_id query param is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parent_id = int(parent_id)
        except ValueError:
            return Response(
                {"error": "parent_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = get_taxonomy_cache_key("CategoryChildrenById", section=section, parent_id=parent_id)
        data = cache.get(cache_key)
        
        if data is None:
            parent = Category.objects.filter(
                id=parent_id,
                section__slug=section,
                is_active=True
            ).first()

            if not parent:
                return Response(
                    {"error": "Parent category not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            children = parent.children.filter(is_active=True).order_by("name", "id")

            data = [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "parent_id": parent.id,
                }
                for c in children
            ]
            cache.set(cache_key, data, TAXONOMY_CACHE_TIMEOUT)

        return Response(data, status=status.HTTP_200_OK)


class TaxonomyTree(APIView):
    """
    GET /api/taxonomy/<section>/tree/ - Full recursive tree (PUBLIC)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section):
        cache_key = get_taxonomy_cache_key("TaxonomyTree", section=section)
        data = cache.get(cache_key)
        
        if data is None:
            def build(node: Category):
                children = node.children.filter(is_active=True).order_by("name", "id")
                return {
                    "id": node.id,
                    "name": node.name,
                    "slug": node.slug,
                    "children": [build(c) for c in children],
                }

            roots = Category.objects.filter(
                section__slug=section,
                parent__isnull=True,
                is_active=True
            ).order_by("name", "id")

            data = [build(r) for r in roots]
            cache.set(cache_key, data, TAXONOMY_CACHE_TIMEOUT)
            
        return Response(data, status=status.HTTP_200_OK)


class TaxonomyByLevels(APIView):
    """
    GET /api/taxonomy/<section>/levels/
    Returns a nested tree structure with level-specific keys:
    Root -> sub_categories -> segments -> topics -> children
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, section):
        cache_key = get_taxonomy_cache_key("TaxonomyByLevels", section=section)
        tree = cache.get(cache_key)
        
        if tree is None:
            def build_tree(node, depth):
                # Define keys for children based on depth
                if depth == 0:
                    child_key = "sub_categories"
                elif depth == 1:
                    child_key = "segments"
                elif depth == 2:
                    child_key = "topics"
                else:
                    child_key = "children"

                children = node.children.filter(is_active=True).order_by("rank", "name")
                
                data = {
                    "id": node.id,
                    "name": node.name,
                    "slug": node.slug,
                    "rank": node.rank,
                    "depth": depth
                }

                if children.exists():
                    data[child_key] = [build_tree(c, depth + 1) for c in children]
                else:
                    data[child_key] = []

                return data

            roots = Category.objects.filter(
                section__slug=section,
                parent__isnull=True,
                is_active=True
            ).order_by("rank", "name")

            tree = [build_tree(r, 0) for r in roots]
            cache.set(cache_key, tree, TAXONOMY_CACHE_TIMEOUT)
            
        return Response(tree, status=status.HTTP_200_OK)


class CategoryList(APIView):
    """
    GET /api/taxonomy/all/ - All categories flat list (PUBLIC)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        cache_key = get_taxonomy_cache_key("CategoryList")
        data = cache.get(cache_key)
        
        if data is None:
            categories = Category.objects.filter(is_active=True).order_by("section__slug", "name")
            data = [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "section": c.section.slug if c.section else None,
                    "parent_id": c.parent_id,
                    "rank": c.rank
                }
                for c in categories
            ]
            cache.set(cache_key, data, TAXONOMY_CACHE_TIMEOUT)
            
        return Response(data, status=status.HTTP_200_OK)


class SectionList(APIView):
    """
    GET /api/taxonomy/sections/
    Get all distinct sections currently in use
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        cache_key = get_taxonomy_cache_key("SectionList")
        data = cache.get(cache_key)
        
        if data is None:
            sections = Section.objects.filter(is_active=True).order_by('rank', 'name')
            data = [{"id": s.slug, "name": s.name} for s in sections]
            cache.set(cache_key, data, TAXONOMY_CACHE_TIMEOUT)
            
        return Response(data, status=status.HTTP_200_OK)
