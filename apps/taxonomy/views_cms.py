from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from apps.common.authentication import JWTAuthentication
from apps.common.permissions import min_role_permission

from .models import Category
from .pagination import CategoryCursorPagination

class AdminCategoryList(APIView):
    """
    CMS
    GET /api/cms/taxonomy/categories/?section=academics&parent_id=1&active=true
    Role: EDITOR+
    """

    #authentication_classes = [JWTAuthentication]
    #permission_classes = [min_role_permission("PUBLISHER")]

    def get(self, request):

        section = request.GET.get("section")
        parent_id = request.GET.get("parent_id")
        active = request.GET.get("active")

        qs = Category.objects.all().order_by("section", "parent_id", "rank", "name", "id")

        if section:
            qs = qs.filter(section=section)

        if parent_id:
            qs = qs.filter(parent_id=int(parent_id))

        if active == "true":
            qs = qs.filter(is_active=True)
        elif active == "false":
            qs = qs.filter(is_active=False)

        paginator = CategoryCursorPagination()
        page = paginator.paginate_queryset(qs, request)
        
        if page is not None:
            results = [
                {
                    "id": c.id,
                    "section": c.section,
                    "name": c.name,
                    "slug": c.slug,
                    "parent_id": c.parent_id,
                    "rank": c.rank,
                    "is_active": c.is_active,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in page
            ]
            
            return paginator.get_paginated_response(results)

        return Response({
            "results": [],
            "next_cursor": None,
            "has_next": False,
            "limit": paginator.page_size
        }, status=200)


class CreateCategory(APIView):
    """
    CMS
    POST /api/cms/taxonomy/categories/
    Role: EDITOR+
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("PUBLISHER")]

    def post(self, request):

        section = (request.data.get("section") or "").strip()
        name = (request.data.get("name") or "").strip()
        slug = (request.data.get("slug") or "").strip()
        parent_id = request.data.get("parent_id")
        rank = int(request.data.get("rank") or 0)
        is_active = bool(request.data.get("is_active", True))

        if not section or not name or not slug:
            return Response({"error": "section, name, slug are required"}, status=400)

        parent = None
        if parent_id:
            parent = get_object_or_404(Category, id=parent_id)
            if parent.section != section:
                return Response({"error": "Parent must be in same section"}, status=400)

        # ✅ prevent duplicates
        if Category.objects.filter(section=section, slug=slug, parent=parent).exists():
            return Response({"error": "Duplicate category in same branch"}, status=409)

        cat = Category.objects.create(
            section=section,
            name=name,
            slug=slug,
            parent=parent,
            rank=rank,
            is_active=is_active,
        )

        return Response(
            {
                "id": cat.id,
                "section": cat.section,
                "name": cat.name,
                "slug": cat.slug,
                "parent_id": cat.parent_id,
                "rank": cat.rank,
                "is_active": cat.is_active,
            },
            status=201,
        )


class UpdateCategory(APIView):
    """
    CMS
    PATCH /api/cms/taxonomy/categories/<id>/
    Role: EDITOR+
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("PUBLISHER")]

    def patch(self, request, category_id):

        cat = get_object_or_404(Category, id=category_id)

        if "name" in request.data:
            cat.name = (request.data.get("name") or "").strip()

        if "slug" in request.data:
            cat.slug = (request.data.get("slug") or "").strip()

        if "rank" in request.data:
            cat.rank = int(request.data.get("rank") or 0)

        if "is_active" in request.data:
            cat.is_active = bool(request.data.get("is_active"))

        if "parent_id" in request.data:
            pid = request.data.get("parent_id")
            if pid in (None, "", 0, "0"):
                cat.parent = None
            else:
                parent = get_object_or_404(Category, id=int(pid))

                if parent.section != cat.section:
                    return Response({"error": "Parent must be in same section"}, status=400)

                # loop detection
                node = parent
                while node:
                    if node.id == cat.id:
                        return Response({"error": "Invalid parent loop detected"}, status=400)
                    node = node.parent

                cat.parent = parent

        # ✅ prevent duplicates
        dup = Category.objects.filter(
            section=cat.section,
            slug=cat.slug,
            parent=cat.parent,
        ).exclude(id=cat.id).exists()

        if dup:
            return Response({"error": "Duplicate slug in same branch"}, status=409)

        cat.save()
        return Response({"status": "updated"}, status=200)


class DeleteCategory(APIView):
    """
    CMS
    DELETE /api/cms/taxonomy/categories/<id>/
    Role: ADMIN ONLY

    ❌ Hard delete only allowed if no children.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("ADMIN")]

    def delete(self, request, category_id):

        cat = get_object_or_404(Category, id=category_id)

        if cat.children.exists():
            return Response({"error": "Cannot delete category with children"}, status=409)

        cat.delete()
        return Response({"status": "deleted"}, status=200)


class DisableCategory(APIView):
    """
    CMS
    PATCH /api/cms/taxonomy/categories/<id>/disable/
    Role: EDITOR+
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("PUBLISHER")]

    def patch(self, request, category_id):

        cat = get_object_or_404(Category, id=category_id)
        cat.is_active = False
        cat.save(update_fields=["is_active"])
        return Response({"status": "disabled"}, status=200)


class EnableCategory(APIView):
    """
    CMS
    PATCH /api/cms/taxonomy/categories/<id>/enable/
    Role: EDITOR+
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("PUBLISHER")]

    def patch(self, request, category_id):

        cat = get_object_or_404(Category, id=category_id)
        cat.is_active = True
        cat.save(update_fields=["is_active"])
        return Response({"status": "enabled"}, status=200)
 