# apps/academics/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Public APIs
    path("levels/", views.LevelList.as_view(), name="level-list"),
    path("subjects/", views.SubjectList.as_view(), name="subject-list"),
    path("categories/", views.CategoryList.as_view(), name="category-list"),
    path("chapters/", views.ChapterList.as_view(), name="chapter-list"),
    path("chapters/<int:pk>/", views.ChapterDetail.as_view(), name="chapter-detail"),
    path("materials/", views.MaterialList.as_view(), name="material-list"),
    path("materials/<int:pk>/", views.MaterialDetail.as_view(), name="material-detail"),

    # Optimized Blocks
    path("level-blocks/", views.LevelBlockSubjects.as_view(), name="level_block_subjects"),
    path("subject-blocks/", views.SubjectBlockMaterials.as_view(), name="subject_block_materials"),
    path("hierarchy/", views.ExamHierarchyList.as_view(), name="exam-hierarchy"),

    # CMS Admin APIs (CRUD)
    path("cms/levels/", views.LevelListCMS.as_view(), name="level-list-cms"),
    path("cms/levels/<int:pk>/", views.LevelDetailCMS.as_view(), name="level-detail-cms"),
    
    path("cms/subjects/", views.SubjectListCMS.as_view(), name="subject-list-cms"),
    path("cms/subjects/<int:pk>/", views.SubjectDetailCMS.as_view(), name="subject-detail-cms"),
    
    path("cms/categories/", views.CategoryListCMS.as_view(), name="category-list-cms"),
    path("cms/categories/<int:pk>/", views.CategoryDetailCMS.as_view(), name="category-detail-cms"),
    
    path("cms/chapters/", views.ChapterListCMS.as_view(), name="chapter-list-cms"),
    path("cms/chapters/<int:pk>/", views.ChapterDetailCMS.as_view(), name="chapter-detail-cms"),
    
    path("cms/materials/", views.MaterialListCMS.as_view(), name="material-list-cms"),
    path("cms/materials/<int:pk>/", views.MaterialDetailCMS.as_view(), name="material-detail-cms"),
]