from django.urls import path
from .views import (
    TaxonomyBySection,
    CategoryChildrenBySlug,
    CategoryChildrenById,
    TaxonomyTree,
    CategoryList,
    SectionList,
)

from .views_cms import (
    CreateCategory,
    UpdateCategory,
    DeleteCategory,
    AdminCategoryList,
    DisableCategory,
    EnableCategory,
)

urlpatterns = [
    # CMS / Admin paths (must come before generic section paths)
    path("categories/", AdminCategoryList.as_view()),
    path("categories/create/", CreateCategory.as_view()),
    path("categories/<int:category_id>/", UpdateCategory.as_view()),
    path("categories/<int:category_id>/delete/", DeleteCategory.as_view()),
    path("categories/<int:category_id>/disable/", DisableCategory.as_view()),
    path("categories/<int:category_id>/enable/", EnableCategory.as_view()),

    # Public / Generic paths
    path("sections/", SectionList.as_view()),  # Distinct sections
    path("all/", CategoryList.as_view()),  # Public full list
    path("<str:section>/", TaxonomyBySection.as_view()),
    path("<str:section>/tree/", TaxonomyTree.as_view()),

    #  BEST (ID-based children)
    path("<str:section>/children/", CategoryChildrenById.as_view()),

    # optional (slug-based children, root only)
    path("<str:section>/<str:slug>/children/", CategoryChildrenBySlug.as_view()),
]
