from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Category, Section



class TaxonomyBySection(APIView):
    """
    GET /api/taxonomy/<section>/
    Root-level categories only (PUBLIC)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section):
        categories = Category.objects.filter(
            section__slug=section,
            parent__isnull=True,
            is_active=True
        ).order_by("name", "id")

        return Response(
            [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                }
                for c in categories
            ],
            status=status.HTTP_200_OK,
        )


class CategoryChildrenBySlug(APIView):
    """
    GET /api/taxonomy/<section>/<slug>/children/
     Only works for ROOT category slug (safe but limited)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section, slug):
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

        return Response(
            [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "parent_id": parent.id,
                }
                for c in children
            ],
            status=status.HTTP_200_OK,
        )


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

        return Response(
            [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "parent_id": parent.id,
                }
                for c in children
            ],
            status=status.HTTP_200_OK,
        )


class TaxonomyTree(APIView):
    """
    GET /api/taxonomy/<section>/tree/ - Full recursive tree (PUBLIC)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, section):
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

        return Response([build(r) for r in roots], status=status.HTTP_200_OK)


class CategoryList(APIView):
    """
    GET /api/taxonomy/all/ - All categories flat list (PUBLIC)
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
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
        return Response(data, status=status.HTTP_200_OK)


class SectionList(APIView):
    """
    GET /api/taxonomy/sections/
    Get all distinct sections currently in use
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        sections = Section.objects.filter(is_active=True).order_by('rank', 'name')
        data = [{"id": s.slug, "name": s.name} for s in sections]
        return Response(data, status=status.HTTP_200_OK)
