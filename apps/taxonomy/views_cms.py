from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from apps.common.authentication import JWTAuthentication
from apps.common.permissions import min_role_permission

from .models import Category, Section
from .pagination import CategoryCursorPagination

class AdminCategoryList(APIView):
    """
    CMS
    GET /api/cms/taxonomy/categories/
    Role: CONTRIBUTOR+
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

    def get(self, request):

        section = request.GET.get("section")
        parent_id = request.GET.get("parent_id")
        active = request.GET.get("active")

        qs = Category.objects.all().order_by("section", "parent_id", "rank", "name", "id")

        if section:
            qs = qs.filter(section__slug=section)

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
                    "section_id": c.section_id,
                    "section_slug": c.section.slug if c.section else None,
                    "name": c.name,
                    "slug": c.slug,
                    "language": c.language,
                    "parent_id": c.parent_id,
                    "rank": c.rank,
                    "is_active": c.is_active,
                    "image_id": c.image_id,
                    "pdf_id": c.pdf_id,
                    "content": c.content,
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


class AdminSectionList(APIView):
    """
    CMS
    GET /api/cms/taxonomy/sections/
    Role: CONTRIBUTOR+
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

    def get(self, request):
        active = request.GET.get("active")
        qs = Section.objects.all().order_by("rank", "name")

        if active == "true":
            qs = qs.filter(is_active=True)
        elif active == "false":
            qs = qs.filter(is_active=False)

        results = [
            {
                "id": s.id,
                "name": s.name,
                "slug": s.slug,
                "rank": s.rank,
                "is_active": s.is_active,
                "created_at": s.created_at,
            }
            for s in qs
        ]
        return Response({"results": results})


class CreateSection(APIView):
    """
    CMS
    POST /api/cms/taxonomy/sections/create/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        slug = (request.data.get("slug") or "").strip()
        rank = int(request.data.get("rank") or 0)

        if not name or not slug:
            return Response({"error": "name and slug are required"}, status=400)

        if Section.objects.filter(slug=slug).exists():
            return Response({"error": "Section with this slug already exists"}, status=409)

        sec = Section.objects.create(name=name, slug=slug, rank=rank)
        return Response({"id": sec.id, "name": sec.name, "slug": sec.slug}, status=201)


class UpdateSection(APIView):
    """
    CMS
    PATCH /api/cms/taxonomy/sections/<id>/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("PUBLISHER")]

    def patch(self, request, section_id):
        sec = get_object_or_404(Section, id=section_id)
        if "name" in request.data:
            sec.name = request.data["name"].strip()
        if "slug" in request.data:
            sec.slug = request.data["slug"].strip()
        if "rank" in request.data:
            sec.rank = int(request.data["rank"] or 0)
        if "is_active" in request.data:
            sec.is_active = bool(request.data["is_active"])
        
        sec.save()
        return Response({"status": "updated"})


class DeleteSection(APIView):
    """
    CMS
    DELETE /api/cms/taxonomy/sections/<id>/
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("ADMIN")]

    def delete(self, request, section_id):
        sec = get_object_or_404(Section, id=section_id)
        if sec.categories.exists():
            return Response({"error": "Cannot delete section with categories"}, status=409)
        sec.delete()
        return Response({"status": "deleted"})


class CreateCategory(APIView):
    """
    CMS
    POST /api/cms/taxonomy/categories/create/
    Role: CONTRIBUTOR+
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [min_role_permission("CONTRIBUTOR")]

    def post(self, request):

        section_id = request.data.get("section_id")
        name = (request.data.get("name") or "").strip()
        slug = (request.data.get("slug") or "").strip()
        language = (request.data.get("language") or "te").strip()
        parent_id = request.data.get("parent_id")
        rank = int(request.data.get("rank") or 0)
        is_active = bool(request.data.get("is_active", True))
        image_id = request.data.get("image_id")
        pdf_id = request.data.get("pdf_id")
        content = request.data.get("content", "")

        if not section_id or not name or not slug:
            return Response({"error": "section_id, name, slug are required"}, status=400)

        section = get_object_or_404(Section, id=section_id)

        parent = None
        if parent_id:
            parent = get_object_or_404(Category, id=parent_id)
            if parent.section_id != section.id:
                return Response({"error": "Parent must be in same section"}, status=400)

        # ✅ prevent duplicates
        if Category.objects.filter(section=section, slug=slug, parent=parent).exists():
            return Response({"error": "Duplicate category in same branch"}, status=409)

        cat = Category.objects.create(
            section=section,
            name=name,
            slug=slug,
            language=language,
            parent=parent,
            rank=rank,
            is_active=is_active,
            image_id=image_id,
            pdf_id=pdf_id,
            content=content
        )

        return Response(
            {
                "id": cat.id,
                "section_id": cat.section_id,
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

        if "section_id" in request.data:
            cat.section = get_object_or_404(Section, id=request.data["section_id"])

        if "name" in request.data:
            cat.name = (request.data.get("name") or "").strip()

        if "slug" in request.data:
            cat.slug = (request.data.get("slug") or "").strip()

        if "language" in request.data:
            cat.language = (request.data.get("language") or "te").strip()

        if "rank" in request.data:
            cat.rank = int(request.data.get("rank") or 0)

        if "is_active" in request.data:
            cat.is_active = bool(request.data.get("is_active"))

        if "image_id" in request.data:
            cat.image_id = request.data.get("image_id")

        if "pdf_id" in request.data:
            cat.pdf_id = request.data.get("pdf_id")

        if "content" in request.data:
            cat.content = request.data.get("content", "")

        if "parent_id" in request.data:
            pid = request.data.get("parent_id")
            if pid in (None, "", 0, "0"):
                cat.parent = None
            else:
                parent = get_object_or_404(Category, id=int(pid))

                if parent.section_id != cat.section_id:
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
 