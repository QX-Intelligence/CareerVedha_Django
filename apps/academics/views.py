from django.core.cache import cache
from rest_framework import generics, filters, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from apps.common.jwt import get_user_from_jwt
from apps.common.permissions import require_min_role, IsAuthenticatedDict
from apps.common.authentication import JWTAuthentication
from .models import AcademicLevel, AcademicSubject, AcademicCategory, AcademicChapter, AcademicMaterial
from .serializers import (
    AcademicLevelSerializer,
    AcademicSubjectSerializer,
    AcademicCategorySerializer,
    AcademicChapterSerializer,
    AcademicChapterDetailSerializer,
    AcademicMaterialSerializer,
    ExamHierarchySerializer,
)
from .cache import get_academics_cache_version, bump_academics_cache
from .utils import prepare_material_card, prepare_subject_card


class LevelList(generics.ListAPIView):
    queryset = AcademicLevel.objects.filter(is_active=True)
    serializer_class = AcademicLevelSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["board"]


class SubjectList(generics.ListAPIView):
    queryset = AcademicSubject.objects.all()
    serializer_class = AcademicSubjectSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["level"]


class CategoryList(generics.ListAPIView):
    queryset = AcademicCategory.objects.all()
    serializer_class = AcademicCategorySerializer


class MaterialList(generics.ListAPIView):
    queryset = AcademicMaterial.objects.filter(status="PUBLISHED", deleted_at__isnull=True)
    serializer_class = AcademicMaterialSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["level", "subject", "category", "chapter"]
    search_fields = ["translations__title"]


class MaterialDetail(generics.RetrieveAPIView):
    queryset = AcademicMaterial.objects.filter(status="PUBLISHED", deleted_at__isnull=True)
    serializer_class = AcademicMaterialSerializer


class ChapterList(generics.ListAPIView):
    queryset = AcademicChapter.objects.filter(is_active=True)
    serializer_class = AcademicChapterSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["subject"]


class ChapterDetail(generics.RetrieveAPIView):
    """Rich Chapter View: Info + Articles + Materials."""
    queryset = AcademicChapter.objects.filter(is_active=True).prefetch_related(
        "translations",
        "materials__translations",
        "materials__media_links__media"
    )
    serializer_class = AcademicChapterDetailSerializer


class LevelBlockSubjects(generics.GenericAPIView):
    """
    Public API: Group Subjects by Level.
    GET /api/academics/level-blocks/
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        board = request.GET.get("board", "AP")
        ver = get_academics_cache_version()
        cache_key = f"v{ver}:academics:level_blocks:{board}"
        
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=200)

        levels = AcademicLevel.objects.filter(board=board, is_active=True).prefetch_related(
            "subjects__media_links__media"
        ).order_by("rank")

        blocks = []
        for lv in levels:
            subject_cards = [prepare_subject_card(s) for s in lv.subjects.all()]
            blocks.append({
                "level": {
                    "id": lv.id,
                    "name": lv.name,
                    "board": lv.board
                },
                "subjects": subject_cards
            })

        cache.set(cache_key, blocks, timeout=3600)
        return Response(blocks, status=200)


class SubjectBlockMaterials(generics.GenericAPIView):
    """
    Public API: Group Materials by Chapter under a Subject.
    GET /api/academics/subject-blocks/?subject_slug=maths&lang=te
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        subject_id = request.GET.get("subject_id")
        lang = request.GET.get("lang", "te")
        if not subject_id:
            return Response({"error": "subject_id is required"}, status=400)

        ver = get_academics_cache_version()
        cache_key = f"v{ver}:academics:subject_blocks:{subject_id}:{lang}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=200)

        try:
            subject = AcademicSubject.objects.get(id=subject_id)
        except AcademicSubject.DoesNotExist:
            return Response({"error": "subject not found"}, status=404)

        chapters = AcademicChapter.objects.filter(subject=subject, is_active=True).prefetch_related(
            "materials__translations", 
            "materials__media_links__media"
        ).order_by("rank")

        blocks = []
        for ch in chapters:
            material_cards = []
            for m in ch.materials.filter(status="PUBLISHED", deleted_at__isnull=True):
                card = prepare_material_card(m, lang)
                if card: material_cards.append(card)
            
            blocks.append({
                "chapter": {
                    "id": ch.id,
                    "name": ch.name
                },
                "materials": material_cards
            })

        cache.set(cache_key, blocks, timeout=3600)
        return Response(blocks, status=200)


# 🛠️ CMS MANAGEMENT VIEWS (CRUD)
# These views require EDITOR+ roles

class CMSBaseView:
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedDict]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

    def perform_destroy(self, instance):
        instance.delete()
        bump_academics_cache()


class LevelListCMS(CMSBaseView, generics.ListCreateAPIView):
    queryset = AcademicLevel.objects.all().order_by("rank")
    serializer_class = AcademicLevelSerializer


class LevelDetailCMS(CMSBaseView, generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicLevel.objects.all()
    serializer_class = AcademicLevelSerializer


class SubjectListCMS(CMSBaseView, generics.ListCreateAPIView):
    queryset = AcademicSubject.objects.select_related("level").prefetch_related(
        "media_links__media", "chapters"
    ).all().order_by("rank")
    serializer_class = AcademicSubjectSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)


class SubjectDetailCMS(CMSBaseView, generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicSubject.objects.select_related("level").prefetch_related(
        "media_links__media", "chapters"
    ).all()
    serializer_class = AcademicSubjectSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)


class CategoryListCMS(CMSBaseView, generics.ListCreateAPIView):
    queryset = AcademicCategory.objects.all().order_by("rank")
    serializer_class = AcademicCategorySerializer


class CategoryDetailCMS(CMSBaseView, generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicCategory.objects.all()
    serializer_class = AcademicCategorySerializer


class ChapterListCMS(CMSBaseView, generics.ListCreateAPIView):
    queryset = AcademicChapter.objects.select_related("subject").all().order_by("rank")
    serializer_class = AcademicChapterSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["subject", "is_active"]
    search_fields = ["name"]


class ChapterDetailCMS(CMSBaseView, generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicChapter.objects.select_related("subject").all()
    serializer_class = AcademicChapterSerializer


class MaterialListCMS(CMSBaseView, generics.ListCreateAPIView):
    queryset = AcademicMaterial.objects.filter(deleted_at__isnull=True).select_related(
        "subject", "category", "chapter"
    ).prefetch_related("translations", "media_links__media")
    serializer_class = AcademicMaterialSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["subject", "category", "chapter", "status"]
    search_fields = ["translations__title"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = get_user_from_jwt(self.request)
        context["user_id"] = user.get("user_id") if user else "system"
        return context


class MaterialDetailCMS(CMSBaseView, generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicMaterial.objects.select_related(
        "subject", "category", "chapter"
    ).prefetch_related("translations", "media_links__media").all() 
    serializer_class = AcademicMaterialSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def perform_destroy(self, instance):
        """Implement soft delete by default. Hard delete if specifically requested."""
        hard_delete = self.request.query_params.get("hard", "false").lower() == "true"
        if hard_delete:
            instance.delete()
        else:
            instance.soft_delete()
        bump_academics_cache()


class ExamHierarchyList(generics.ListAPIView):
    """
    Public API: Complete Levels -> Subjects -> Chapters hierarchy for external systems.
    """
    queryset = AcademicLevel.objects.filter(is_active=True).prefetch_related(
        "subjects__chapters"
    ).order_by("rank")
    serializer_class = ExamHierarchySerializer