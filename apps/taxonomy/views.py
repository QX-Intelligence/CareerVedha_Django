from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Category
from apps.common.permissions import min_role_permission
from apps.common.authentication import JWTAuthentication


class TaxonomyBySection(APIView):
    """
    GET /api/taxonomy/<section>/
    Root-level categories only
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

    def get(self, request, section):
        categories = Category.objects.filter(
            section=section,
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
    ✅ Only works for ROOT category slug (safe but limited)
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

    def get(self, request, section, slug):
        parent = Category.objects.filter(
            section=section,
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
    ✅ BEST API
    GET /api/taxonomy/<section>/children/?parent_id=12
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

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
            section=section,
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
    GET /api/taxonomy/<section>/tree/
    Full tree
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

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
            section=section,
            parent__isnull=True,
            is_active=True
        ).order_by("name", "id")

        return Response([build(r) for r in roots], status=status.HTTP_200_OK)


class CategoryList(APIView):
    """
    GET /api/taxonomy/all/
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

    def get(self, request):
        categories = Category.objects.filter(is_active=True).order_by("section", "name")
        data = [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "section": c.section,
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
        sections = Category.objects.filter(is_active=True).values_list('section', flat=True).distinct().order_by('section')
        # Return as objects with id (slug) and name (capitalized)
        data = [{"id": s, "name": s.upper()} for s in sections if s]
        return Response(data, status=status.HTTP_200_OK)
