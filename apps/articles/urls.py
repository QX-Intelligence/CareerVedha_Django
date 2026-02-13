from django.urls import path

from .views_cms import (
    CreateArticle,
    AddOrUpdateTranslation,
    AssignCategories,
    MoveToReview,
    PublishArticle,
    DeactivateArticle,
    ActivateArticle,
    AdminArticleList,
    ArticleRevisionList,
    ArticleDelete,
    ArticleSearch,
    ArticleDeleteMulti,
    ArticleReject,
    AdminArticleSearchSuggestions,
    AdminArticleDirectPublish
)

from .views_attach import AttachMediaToArticle

from .views_feature import PinFeature, UnpinFeature, GetFeatures

from .views_section import HomeFeed, SectionFeed
from .views_public import PublicArticle
from .views_list_cursor import PublicArticlesListCursor
from .views_published import PublishedArticlesList
from .views_trending import TrendingArticles
from .views_filters import ArticleFilters
from .views_category_block import CategoryBlockArticles     
from .views_track import TrackArticleView
from .views_suggestions import ArticleSearchSuggestions
from .views_attach import AttachMediaToArticle
from .views_current_affairs import CurrentAffairsView

urlpatterns = [
    # ==========================
    # CMS
    # ==========================
    path("", CreateArticle.as_view()),
    path("<int:article_id>/translation/", AddOrUpdateTranslation.as_view()),
    path("<int:article_id>/media/", AttachMediaToArticle.as_view()),
    path("<int:article_id>/categories/", AssignCategories.as_view()),
    path("<int:article_id>/review/", MoveToReview.as_view()),
    path("<int:article_id>/publish/", PublishArticle.as_view()),
    path("<int:article_id>/direct-publish/", AdminArticleDirectPublish.as_view()),
    path("<int:article_id>/deactivate/", DeactivateArticle.as_view()),
    path("<int:article_id>/activate/", ActivateArticle.as_view()),
    path("<int:article_id>/reject/", ArticleReject.as_view()),
    path("<int:article_id>/", ArticleDelete.as_view()),
    path("delete-multi/", ArticleDeleteMulti.as_view()),
    path("search/", ArticleSearch.as_view()),
    path("admin/list/", AdminArticleList.as_view()),
    path("admin/search-suggestions/", AdminArticleSearchSuggestions.as_view()),
    path("<int:article_id>/revisions/", ArticleRevisionList.as_view()),
    # ==========================
    # CMS Features
    # ==========================
    path("<int:article_id>/feature/", PinFeature.as_view()),
    path("<int:article_id>/feature/remove/", UnpinFeature.as_view()),
    path("features/", GetFeatures.as_view()),

    # ==========================
    # PUBLIC
    # ==========================
    path("home/", HomeFeed.as_view()),
    path("section/<str:section>/", SectionFeed.as_view()),
    path("list/", PublicArticlesListCursor.as_view()),
    path("published/", PublishedArticlesList.as_view()),
    path("trending/", TrendingArticles.as_view()),
    path("filters/", ArticleFilters.as_view()),
    path("search-suggestions/", ArticleSearchSuggestions.as_view()),
    path("category-block/", CategoryBlockArticles.as_view()),
    path("current-affairs/", CurrentAffairsView.as_view()),
    path("<str:section>/<slug:slug>/track-view/", TrackArticleView.as_view()),
    path("<str:section>/<slug:slug>/", PublicArticle.as_view()),
]