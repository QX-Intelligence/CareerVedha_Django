from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from apps.articles.sitemaps import ArticleSitemap
from apps.jobs.sitemaps import JobsSitemap
from apps.articles.views_public import PublicArticle

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                       CMS API - COMPLETE URL DOCUMENTATION                    ║
║                     FOR FRONTEND DEVELOPERS - EASY REFERENCE                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝

PROJECT: Django CMS Service
BASE URL: http://localhost:8000 (development) | https://api.example.com (production)

AUTHENTICATION:
• Protected endpoints require JWT token in Authorization header
• Format: Authorization: Bearer <jwt_token>
• Roles: CONTRIBUTOR < EDITOR < PUBLISHER < ADMIN

ERROR RESPONSES:
• 400 Bad Request - Invalid parameters or missing required fields
• 401 Unauthorized - No JWT token provided
• 403 Forbidden - Insufficient permissions/role
• 404 Not Found - Resource doesn't exist
• 410 Gone - Resource expired or no longer available
• 500 Internal Server Error - Server error

PAGINATION/LIMITING:
• Use ?limit parameter to control result size (default: 20, max: 50)
• Use ?offset parameter for pagination
• Use ?lang parameter for language (default: "te" for Telugu)

═══════════════════════════════════════════════════════════════════════════════
"""

urlpatterns = [
    # ╔═══════════════════════════════════════════════════════════════════════════╗
    # ║ 1. TAXONOMY/CATEGORIES API - Hierarchical Category Management            ║
    # ╚═══════════════════════════════════════════════════════════════════════════╝
    # Location: apps/taxonomy/ (views.py, urls.py)
    # Public API - No authentication required
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/taxonomy/<section>/
    # ───────────────────────────────────────────────────────────────────────────
    # Root-level categories for a section (pagination friendly)
    # Parameters: section (str, required) - e.g., "academics", "business", "tech"
    # Query: ?offset=0&limit=20
    #
    # Response 200 OK:
    # [
    #   {
    #     "id": 1,
    #     "section": "academics",
    #     "name": "Intermediate",
    #     "slug": "intermediate",
    #     "parent_id": null,
    #     "rank": 0,
    #     "is_active": true,
    #     "created_at": "2026-01-23T09:51:29.194108Z",
    #     "updated_at": "2026-01-23T09:51:29.550484Z"
    #   },
    #   {
    #     "id": 2,
    #     "section": "academics",
    #     "name": "Syllabus",
    #     "slug": "syllabus",
    #     "parent_id": 1,
    #     "rank": 0,
    #     "is_active": true,
    #     "created_at": "2026-01-23T09:51:29.194108Z",
    #     "updated_at": "2026-01-23T09:51:29.550484Z"
    #   }
    # ]
    # Implementation: TaxonomyBySection.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/taxonomy/<section>/tree/
    # ───────────────────────────────────────────────────────────────────────────
    # Complete hierarchical tree with all nested children (RECURSIVE)
    # Parameters: section (str, required)
    #
    # Response 200 OK:
    # [
    #   {
    #     "id": 1,
    #     "section": "academics",
    #     "name": "Programming",
    #     "slug": "programming",
    #     "parent_id": null,
    #     "rank": 0,
    #     "is_active": true,
    #     "children": [
    #       {
    #         "id": 10,
    #         "section": "academics",
    #         "name": "Python",
    #         "slug": "python",
    #         "parent_id": 1,
    #         "rank": 1,
    #         "is_active": true,
    #         "children": [
    #           {
    #             "id": 100,
    #             "section": "academics",
    #             "name": "Django",
    #             "slug": "django",
    #             "parent_id": 10,
    #             "rank": 0,
    #             "is_active": true,
    #             "children": []
    #           }
    #         ]
    #       }
    #     ]
    #   }
    # ]
    # Implementation: TaxonomyTree.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/taxonomy/<section>/children/?parent_id=<id>
    # ───────────────────────────────────────────────────────────────────────────
    # Get direct children of a category (using parent ID - BEST METHOD)
    # Parameters: section (str), parent_id (int, query parameter)
    #
    # Response 200 OK:
    # [
    #   {
    #     "id": 10,
    #     "section": "academics",
    #     "name": "Python",
    #     "slug": "python",
    #     "parent_id": 1,
    #     "rank": 1,
    #     "is_active": true,
    #     "created_at": "2026-01-23T09:51:29.194108Z",
    #     "updated_at": "2026-01-23T09:51:29.550484Z"
    #   },
    #   {
    #     "id": 11,
    #     "section": "academics",
    #     "name": "JavaScript",
    #     "slug": "javascript",
    #     "parent_id": 1,
    #     "rank": 2,
    #     "is_active": true,
    #     "created_at": "2026-01-23T09:51:29.194108Z",
    #     "updated_at": "2026-01-23T09:51:29.550484Z"
    #   }
    # ]
    # Error 400: {"error": "parent_id query param is required"}
    # Error 400: {"error": "parent_id must be an integer"}
    # Implementation: CategoryChildrenById.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/taxonomy/<section>/<slug>/children/
    # ───────────────────────────────────────────────────────────────────────────
    # Get direct children by parent slug (ROOT CATEGORIES ONLY - LIMITED)
    # Parameters: section (str), slug (str - parent slug)
    #
    # Response 200 OK:
    # [
    #   {
    #     "id": 10,
    #     "section": "academics",
    #     "name": "Python",
    #     "slug": "python",
    #     "parent_id": 1,
    #     "rank": 1,
    #     "is_active": true,
    #     "created_at": "2026-01-23T09:51:29.194108Z",
    #     "updated_at": "2026-01-23T09:51:29.550484Z"
    #   },
    #   {
    #     "id": 11,
    #     "section": "academics",
    #     "name": "JavaScript",
    #     "slug": "javascript",
    #     "parent_id": 1,
    #     "rank": 2,
    #     "is_active": true,
    #     "created_at": "2026-01-23T09:51:29.194108Z",
    #     "updated_at": "2026-01-23T09:51:29.550484Z"
    #   }
    # ]
    # Error 404: {"error": "Category not found"}
    # Implementation: CategoryChildrenBySlug.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # CMS CATEGORY MANAGEMENT ENDPOINTS
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/taxonomy/categories/ - AdminCategoryList
    # POST /api/django/taxonomy/categories/create/ - CreateCategory
    # PATCH /api/django/taxonomy/categories/<id>/ - UpdateCategory
    # DELETE /api/django/taxonomy/categories/<id>/delete/ - DeleteCategory
    # Auth: JWT required | Role: ADMIN
    #
    # ───────────────────────────────────────────────────────────────────────────
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/taxonomy/categories/<category_id>/disable/
    # ───────────────────────────────────────────────────────────────────────────
    # Disable category (set is_active=False)
    # Auth: JWT required | Role: EDITOR+
    # Response 200 OK: { "status": "disabled" }
    # Implementation: DisableCategory.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/taxonomy/categories/<category_id>/enable/
    # ───────────────────────────────────────────────────────────────────────────
    # Enable category (set is_active=True)
    # Auth: JWT required | Role: EDITOR+
    # Response 200 OK: { "status": "enabled" }
    # Implementation: EnableCategory.patch()
    #9
    path("api/django/taxonomy/", include("apps.taxonomy.urls")),
    path("api/django/cms/taxonomy/", include("apps.taxonomy.urls")),
    
    # ╔═══════════════════════════════════════════════════════════════════════════╗
    # ║ 2. ARTICLES API - Content Management System                              ║
    # ╚═══════════════════════════════════════════════════════════════════════════╝
    # Location: apps/articles/ (views_cms.py, views_public.py, views_*.py)
    #
    # ═══════════════════════════════════════════════════════════════════════════
    # CMS ENDPOINTS (Protected - Require Authentication)
    # ═══════════════════════════════════════════════════════════════════════════
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/
    # ───────────────────────────────────────────────────────────────────────────
    # Create new article (DRAFT status)
    # Auth: JWT required | Role: CONTRIBUTOR+
    #
    # Request Body:
    # {
    #   "slug": "article-slug",
    #   "section": "academics",
    #   "status": "DRAFT",
    #   "summary": "Brief summary of article",
    #   "tags": ["tag1", "tag2"],
    #   "keywords": ["keyword1", "keyword2"],
    #   "canonical_url": "https://example.com/article",
    #   "meta_title": "SEO Title",
    #   "meta_description": "SEO Description",
    #   "noindex": false,
    #   "og_title": "Open Graph Title",
    #   "og_description": "OG Description",
    #   "og_image_url": "https://image.url",
    #   "expires_at": "2026-03-31T23:59:59Z",
    #   "translations": [
    #     {
    #       "language": "te",
    #       "title": "Article Title",
    #       "content": "<p>HTML content</p>"
    #     }
    #   ]
    # }
    #
    # Response 201 Created:
    # {
    #   "id": 1,
    #   "slug": "ap-inter-syllabus-2025",
    #   "section": "academics",
    #   "status": "DRAFT",
    #   "summary": "Complete intermediate syllabus coverage",
    #   "tags": ["ap inter", "syllabus"],
    #   "keywords": ["syllabus", "intermediate"],
    #   "canonical_url": "https://example.com/articles/academics/ap-inter-syllabus-2025/",
    #   "meta_title": "AP Intermediate Syllabus 2025",
    #   "meta_description": "Complete syllabus",
    #   "noindex": false,
    #   "og_title": "AP Intermediate Syllabus",
    #   "og_description": "Syllabus coverage",
    #   "og_image_url": "https://cdn.example.com/image.jpg",
    #   "expires_at": null,
    #   "views_count": 0,
    #   "published_at": null,
    #   "created_at": "2026-01-24T10:00:00Z",
    #   "updated_at": "2026-01-24T10:00:00Z",
    #   "translations": [],
    #   "category_ids": []
    # }
    # Error 400: {"error": "Invalid request data"}
    # Implementation: CreateArticle.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/<article_id>/translation/
    # ───────────────────────────────────────────────────────────────────────────
    # Add/update translation + creates revision
    # Auth: JWT required | Role: EDITOR+
    #
    # Request Body:
    # {
    #   "language": "te",
    #   "title": "Article Title in Telugu",
    #   "content": "<p>HTML content here</p>",
    #   "note": "Editor notes (optional)"
    # }
    #
    # Response 200 OK: { "status": "saved" }
    # Error 400: {"error": "language, title, content required"}
    # Implementation: AddOrUpdateTranslation.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/<article_id>/media/
    # ───────────────────────────────────────────────────────────────────────────
    # Attach media to article (Cross-service reference)
    # Auth: JWT required | Role: EDITOR+
    #
    # Request Body:
    # {
    #   "media_id": 123,     # Required (BigInteger)
    #   "usage": "INLINE",   # Optional (default: INLINE)
    #   "position": 1        # Optional (default: 0)
    # }
    #
    # Response 201 Created: { "status": "attached" }
    # Error 400: { "error": "media_id is required" }
    # Implementation: AttachMediaToArticle.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/<article_id>/categories/
    # ───────────────────────────────────────────────────────────────────────────
    # Assign categories to article
    # Auth: JWT required | Role: EDITOR+
    #
    # Request Body:
    # { "category_ids": [1, 2, 3] }
    #
    # Response 200 OK: { "status": "categories updated" }
    # Error 400: {"error": "category_ids must be a list"}
    # Implementation: AssignCategories.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/review/
    # ───────────────────────────────────────────────────────────────────────────
    # Move article DRAFT → REVIEW (validates Telugu translation + categories)
    # Auth: JWT required | Role: EDITOR+
    # Validation Rules:
    # • Must have Telugu (te) translation
    # • Must have at least 1 category assigned
    #
    # Response 200 OK: { "status": "review" }
    # Error 400: {"error": "Telugu translation (te) required"}
    # Error 400: {"error": "At least 1 category required"}
    # Implementation: MoveToReview.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/publish/
    # ───────────────────────────────────────────────────────────────────────────
    # Move article REVIEW → PUBLISHED (sets noindex=False, published_at=now)
    # Auth: JWT required | Role: PUBLISHER+
    # Validation Rules:
    # • Article must be in REVIEW status
    # • Must have Telugu (te) translation
    #
    # Response 200 OK: { "status": "published" }
    # Error 400: {"error": "Must be REVIEW before publish"}
    # Error 400: {"error": "Telugu translation (te) required"}
    # Implementation: PublishArticle.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/deactivate/
    # ───────────────────────────────────────────────────────────────────────────
    # Deactivate article (status=INACTIVE, noindex=True)
    # Auth: JWT required | Role: PUBLISHER+
    #
    # Response 200 OK: { "status": "inactive" }
    # Implementation: DeactivateArticle.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/activate/
    # ───────────────────────────────────────────────────────────────────────────
    # Activate inactive article (status=DRAFT, noindex=True)
    # Allows re-review of previously deactivated articles
    # Auth: JWT required | Role: PUBLISHER+
    #
    # Response 200 OK: { "status": "active" }
    # Implementation: ActivateArticle.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/admin/list/
    # ───────────────────────────────────────────────────────────────────────────
    # Admin list all articles (paginated)
    # Auth: JWT required | Role: EDITOR+
    # Query: ?offset=0&limit=20
    #
    # Response 200 OK:
    # [ { article1 }, { article2 }, ... ]
    # Implementation: AdminArticleList.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/<article_id>/revisions/
    # ───────────────────────────────────────────────────────────────────────────
    # Get revision history of article
    # Auth: JWT required | Role: EDITOR+
    #
    # Response 200 OK:
    # [ { revision1 }, { revision2 }, ... ]
    # Implementation: ArticleRevisionList.get()
    #
    # ═════════════════════════════════════════════════════════════════════════════
    # ▌ ARTICLE FEATURES - Pin to Top/Hero/Breaking ▌
    # ═════════════════════════════════════════════════════════════════════════════
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/features/?feature_type=TOP&section=academics&limit=50
    # ───────────────────────────────────────────────────────────────────────────
    # Get list of all pinned/featured articles (CMS MANAGEMENT)
    # Auth: JWT required | Role: PUBLISHER+ (SUPER_ADMIN, ADMIN, EDITOR, PUBLISHER)
    # Query: ?feature_type=TOP&section=academics&limit=50
    # Feature types: TOP, HERO, BREAKING, EDITOR_PICK
    #
    # Response 200 OK:
    # {
    #   "feature_type": "TOP",
    #   "section": "academics",
    #   "limit": 50,
    #   "count": 5,
    #   "features": [
    #     {
    #       "feature_id": 1,
    #       "article_id": 42,
    #       "article_slug": "django-tutorial",
    #       "article_title": "Django Tutorial",
    #       "section": "academics",
    #       "rank": 1,
    #       "is_active": true,
    #       "is_live": true,
    #       "created_at": "2026-01-20T10:00:00Z",
    #       "ended_at": null
    #     },
    #     {
    #       "feature_id": 2,
    #       "article_id": 43,
    #       "article_slug": "python-basics",
    #       "article_title": "Python Basics",
    #       "section": "academics",
    #       "rank": 2,
    #       "is_active": true,
    #       "is_live": true,
    #       "created_at": "2026-01-19T15:30:00Z",
    #       "ended_at": null
    #     }
    #   ]
    # }
    # Error 400: {"feature_type": "Invalid. Allowed: ['HERO', 'TOP', 'BREAKING', 'EDITOR_PICK']"}
    # Error 403: {"detail": "Insufficient permissions"}
    # Implementation: GetFeatures.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/<id>/feature/
    # ───────────────────────────────────────────────────────────────────────────
    # Pin article as featured (Top/Hero/Breaking/Editor Pick)
    # Auth: JWT required | Role: PUBLISHER+ (SUPER_ADMIN, ADMIN, EDITOR, PUBLISHER)
    #
    # Request Body:
    # {
    #   "feature_type": "TOP",
    #   "rank": 1,
    #   "section": "academics"
    # }
    # Feature types: TOP (limit:10), HERO (limit:5), BREAKING (limit:1), EDITOR_PICK (limit:20)
    # Limits: When feature count exceeds limit, oldest items are deactivated automatically
    #
    # Response 200 OK:
    # {
    #   "status": "featured",
    #   "feature_id": 1,
    #   "feature_type": "TOP",
    #   "section": "academics",
    #   "rank": 1
    # }
    # Implementation: PinFeature.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # DELETE /api/django/cms/articles/<id>/feature/remove/?feature_type=TOP&section=academics
    # ───────────────────────────────────────────────────────────────────────────
    # Unpin featured article
    # Auth: JWT required | Role: PUBLISHER+
    # Query: ?feature_type=TOP&section=academics (required)
    #
    # Response 200 OK: { "status": "unfeatured", "deleted": 1 }
    # Implementation: UnpinFeature.delete()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/features/?feature_type=TOP&section=academics
    # ───────────────────────────────────────────────────────────────────────────
    # Get list of pinned/featured articles - CODE NOT YET IMPLEMENTED
    # Auth: JWT required | Role: PUBLISHER+
    # Query: ?feature_type=TOP&section=academics (required)
    #
    # Response 200 OK (PROPOSED):
    # {
    #   "feature_type": "TOP",
    #   "section": "academics",
    #   "features": [
    #     {
    #       "feature_id": 1,
    #       "article_id": 42,
    #       "article_slug": "django-tutorial",
    #       "article_title": "Django Tutorial",
    #       "rank": 1,
    #       "is_active": true,
    #       "created_at": "2026-01-20T10:00:00Z"
    #     },
    #     ...
    #   ]
    # }
    # Implementation: GetFeatures.get() [NOT YET IMPLEMENTED]
    #
    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC ENDPOINTS (No Authentication Required)
    # ═══════════════════════════════════════════════════════════════════════════
    # NOTE: These endpoints are under /api/django/cms/articles/ prefix but serve public content
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/<section>/<slug>/?lang=te
    # ───────────────────────────────────────────────────────────────────────────
    # Get single published article (DETAIL PAGE)
    # Parameters: section (str), slug (str), lang (str, query, default: "te")
    # No authentication required
    # Status codes: 200 OK | 404 Not Found | 410 Gone
    #
    # Response 200 OK:
    # {
    #   "id": 1,
    #   "slug": "ap-inter-syllabus-2025",
    #   "section": "academics",
    #   "title": "AP ఇంటర్‌మీడియట్ సిలేబస్",
    #   "content": "<p>Complete syllabus coverage...</p>",
    #   "summary": "Complete intermediate syllabus coverage",
    #   "tags": ["ap inter", "syllabus", "2025"],
    #   "keywords": ["syllabus", "intermediate", "subjects"],
    #   "canonical": "https://example.com/articles/academics/ap-inter-syllabus-2025/",
    #   "noindex": false,
    #   "meta": {
    #     "title": "AP Intermediate Syllabus 2025",
    #     "description": "Complete syllabus for AP Intermediate"
    #   },
    #   "og": {
    #     "title": "AP Intermediate Syllabus 2025",
    #     "description": "Complete syllabus coverage",
    #     "image": "https://cdn.example.com/image.jpg"
    #   },
    #   "published_at": "2026-01-09T05:28:09.452431Z",
    #   "created_at": "2026-01-09T05:28:09.452431Z",
    #   "updated_at": "2026-01-24T06:23:29.276563Z"
    # }
    # Error 404: {"error": "Not found"} - unpublished
    # Error 410: {"error": "Not available"} - inactive
    # Error 410: {"error": "Expired"} - past expires_at date
    # Implementation: PublicArticle.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/home/?lang=te&limit=10
    # ───────────────────────────────────────────────────────────────────────────
    # Home feed - featured + trending + latest articles
    # No authentication required
    # Query: ?lang=te&limit=10&offset=0
    #
    # Response 200 OK:
    # {
    #   "featured": [
    #     {
    #       "id": 1,
    #       "slug": "top-article",
    #       "section": "tech",
    #       "title": "Top Story Title",
    #       "summary": "Brief summary...",
    #       "og_image_url": "https://image.url",
    #       "published_at": "2026-01-20T10:00:00Z",
    #       "views_count": 450
    #     },
    #     ...
    #   ],
    #   "trending": [
    #     { "id": 2, "slug": "trending-1", ... },
    #     ...
    #   ],
    #   "latest": [
    #     { "id": 3, "slug": "latest-1", ... },
    #     ...
    #   ]
    # }
    # Implementation: HomeFeed.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/section/<section>/?lang=te&limit=20
    # ───────────────────────────────────────────────────────────────────────────
    # Section feed - articles from specific section
    # Parameters: section (str, required)
    # Query: ?lang=te&limit=20&offset=0
    #
    # Response 200 OK:
    # {
    #   "featured": [ { article_card }, ... ],
    #   "latest": [ { article_card }, ... ]
    # }
    # Implementation: SectionFeed.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/trending/?section=academics&limit=20&lang=te
    # ───────────────────────────────────────────────────────────────────────────
    # Trending articles (by views, most recent first)
    # Query: ?section=academics&limit=20&lang=te
    #
    # Response 200 OK:
    # {
    #   "results": [
    #     {
    #       "id": 5,
    #       "slug": "trending-article",
    #       "section": "academics",
    #       "summary": "...",
    #       "views_count": 5430,
    #       "published_at": "2026-01-15T10:00:00Z"
    #     },
    #     ...
    #   ],
    #   "limit": 20
    # }
    # Implementation: TrendingArticles.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/search-suggestions/?q=django&lang=te&section=academics
    # ───────────────────────────────────────────────────────────────────────────
    # Article search suggestions (published only, searches title & summary)
    # Query: ?q=search_term&lang=te&section=academics (optional)
    # Min query length: 2 characters
    #
    # Response 200 OK:
    # {
    #   "suggestions": [
    #     { "id": 1, "slug": "django-tutorial", "section": "tech", "title": "Django Tutorial" },
    #     { "id": 2, "slug": "django-rest", "section": "tech", "title": "Django REST Framework" },
    #     ...
    #   ]
    # }
    # Implementation: ArticleSearchSuggestions.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/filters/?section=academics
    # ───────────────────────────────────────────────────────────────────────────
    # Get available filter options + article count per category
    # Query: ?section=academics (optional)
    #
    # Response 200 OK:
    # {
    #   "section": "academics",
    #   "total_published": 145,
    #   "top_categories": [
    #     {"category_id": 1, "count": 42},
    #     {"category_id": 2, "count": 38},
    #     ...
    #   ]
    # }
    # Implementation: ArticleFilters.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/category-block/?section=academics&lang=te&limit=6
    # ───────────────────────────────────────────────────────────────────────────
    # Articles grouped by root categories for display blocks
    # Parameters: section (str, required)
    # Query: ?lang=te&limit=6
    #
    # Response 200 OK:
    # {
    #   "blocks": [
    #     {
    #       "category": { "id": 1, "name": "Programming", "slug": "programming" },
    #       "articles": [
    #         {
    #           "id": 10,
    #           "slug": "python-tutorial",
    #           "section": "academics",
    #           "title": "Python Tutorial",
    #           "summary": "Learn Python basics...",
    #           "og_image_url": "https://image.url",
    #           "published_at": "2026-01-18T10:00:00Z",
    #           "views_count": 234
    #         },
    #         ...
    #       ]
    #     },
    #     ...
    #   ]
    # }
    # Implementation: CategoryBlockArticles.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/<section>/<slug>/track-view/
    # ───────────────────────────────────────────────────────────────────────────
    # Track article view - increments views_count + records view event
    # Parameters: section (str), slug (str)
    # No authentication required
    #
    # Response 200 OK: { "status": "ok" }
    # Error 404: { "error": "Not found" } - article not published
    # Implementation: TrackArticleView.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/list/?section=academics&limit=20&cursor=ABC
    # ───────────────────────────────────────────────────────────────────────────
    # All articles with cursor-based pagination (PUBLIC)
    # Query: ?section=academics&limit=20&cursor=ABC
    # Cursor-based: More efficient pagination for large datasets
    # No authentication required
    #
    # Response 200 OK:
    # {
    #   "results": [
    #     {
    #       "id": 1,
    #       "slug": "article-slug",
    #       "section": "academics",
    #       "summary": "Summary text",
    #       "published_at": "2026-01-09T05:28:09Z",
    #       "created_at": "2026-01-09T05:28:09Z"
    #     },
    #     ...
    #   ],
    #   "next_cursor": "XYZ",
    #   "has_next": true,
    #   "limit": 20
    # }
    # Implementation: PublicArticlesListCursor.get()
    #
    # ═════════════════════════════════════════════════════════════════════════════
    # ▌ CMS ARTICLES ENDPOINTS (PROTECTED - JWT REQUIRED) ▌
    # ═════════════════════════════════════════════════════════════════════════════
    # All CMS endpoints require JWT auth. Role required: CONTRIBUTOR+ < EDITOR+ < PUBLISHER+ < ADMIN+ < SUPER_ADMIN
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/
    # ───────────────────────────────────────────────────────────────────────────
    # Create new article in DRAFT status (CONTRIBUTOR+)
    # Supports 2 input methods: direct language fields OR nested translations array
    #
    # Request Body (Direct Fields Method - RECOMMENDED):
    # {
    #   "slug": "my-article",
    #   "section": "academics",
    #   "eng_title": "English Title",
    #   "eng_content": "<p>English content</p>",
    #   "tel_title": "తెలుగు శీర్షిక",
    #   "tel_content": "<p>తెలుగు కంటెంట్</p>",
    #   "category_ids": [1, 2, 3]
    # }
    #
    # Response 201 Created:
    # { "id": 1, "slug": "my-article", "section": "academics", "status": "DRAFT", "title": "తెలుగు శీర్షిక", "created_at": "2026-01-20T10:00:00Z" }
    # Errors: 400 (invalid data), 403 (insufficient role)
    # Implementation: CreateArticle.post() [apps/articles/views_cms.py]
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/<article_id>/translation/
    # ───────────────────────────────────────────────────────────────────────────
    # Add or update article translation + create revision history (EDITOR+)
    #
    # Request Body:
    # {
    #   "language": "en",
    #   "title": "English Title",
    #   "content": "<p>English content</p>",
    #   "summary": "Summary",
    #   "tags": ["tag1"],
    #   "keywords": ["key1"],
    #   "canonical": "https://original.com"
    # }
    #
    # Response 201 Created: { "language": "en", "title": "English Title", "revision_id": 1 }
    # Errors: 400 (duplicate language), 404, 403
    # Implementation: AddOrUpdateTranslation.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/review/
    # ───────────────────────────────────────────────────────────────────────────
    # Move DRAFT → REVIEW. Validates: Telugu translation exists, ≥1 category (CONTRIBUTOR+)
    # Response 200 OK: { "status": "review" }
    # Errors: 400 (validation), 404, 403
    # Implementation: MoveToReview.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/publish/
    # ───────────────────────────────────────────────────────────────────────────
    # Move REVIEW → PUBLISHED. Sets published_at, noindex=false (PUBLISHER+)
    # Response 200 OK: { "id": 1, "status": "PUBLISHED", "published_at": "..." }
    # Implementation: PublishArticle.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/deactivate/
    # ───────────────────────────────────────────────────────────────────────────
    # Deactivate article: status=INACTIVE, noindex=true. Sends notification (ADMIN+)
    # Response 200 OK: { "id": 1, "status": "INACTIVE", "noindex": true }
    # Implementation: DeactivateArticle.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/activate/
    # ───────────────────────────────────────────────────────────────────────────
    # Reactivate INACTIVE article back to DRAFT (ADMIN+)
    # Response 200 OK: { "id": 1, "status": "DRAFT" }
    # Implementation: ActivateArticle.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/reject/
    # ───────────────────────────────────────────────────────────────────────────
    # Reject article REVIEW → DRAFT with reason. Notifies CONTRIBUTOR (EDITOR+)
    # Request: { "reason": "Content quality issue" }
    # Response 200 OK: { "id": 1, "status": "DRAFT", "rejection_reason": "..." }
    # Implementation: ArticleReject.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/articles/<article_id>/
    # ───────────────────────────────────────────────────────────────────────────
    # Update article metadata (summary, tags, keywords, SEO fields, etc.)
    # Auth: JWT required | Role: EDITOR+
    # Note: For updating article title/content, use /translation/ endpoint
    #
    # Request Body (all optional - only include fields to update):
    # {
    #   "summary": "New article summary",
    #   "tags": ["tag1", "tag2", "tag3"],
    #   "keywords": ["keyword1", "keyword2"],
    #   "canonical_url": "https://example.com/original",
    #   "meta_title": "SEO Title (55 chars)",
    #   "meta_description": "SEO Description (160 chars)",
    #   "og_title": "Social Media Title",
    #   "og_description": "Social Media Description",
    #   "og_image_url": "https://cdn.example.com/image.jpg",
    #   "noindex": false,
    #   "expires_at": "2026-03-31T23:59:59Z"
    # }
    #
    # Response 200 OK:
    # {
    #   "id": 1,
    #   "status": "updated",
    #   "summary": "New article summary",
    #   "tags": ["tag1", "tag2", "tag3"],
    #   "keywords": ["keyword1", "keyword2"],
    #   "canonical_url": "https://example.com/original",
    #   "meta_title": "SEO Title",
    #   "meta_description": "SEO Description",
    #   "og_title": "Social Media Title",
    #   "og_description": "Social Media Description",
    #   "og_image_url": "https://cdn.example.com/image.jpg",
    #   "noindex": false,
    #   "expires_at": "2026-03-31T23:59:59Z"
    # }
    # Implementation: ArticleDelete.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # DELETE /api/django/cms/articles/<article_id>/
    # ───────────────────────────────────────────────────────────────────────────
    # Delete single article with audit trail. Sends notification
    # Auth: JWT required | Role: ADMIN+ (SUPER_ADMIN, ADMIN)
    #
    # Response 204 No Content
    # Implementation: ArticleDelete.delete()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # DELETE /api/django/cms/articles/delete-multi/
    # ───────────────────────────────────────────────────────────────────────────
    # Bulk delete multiple articles (ADMIN+)
    # Request: { "article_ids": [1, 2, 3] }
    # Response 200 OK: { "deleted": 3, "failed": 0, "errors": [] }
    # Implementation: ArticleDeleteMulti.delete()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/articles/search/?q=django&section=tech
    # ───────────────────────────────────────────────────────────────────────────
    # Search articles by ID (numeric) or title (EDITOR+)
    # Query: ?q=1 (by ID) | ?q=django (by title) | &section=tech | &status=DRAFT,PUBLISHED
    # Response 200 OK: { "results": [...], "total": N }
    # Implementation: ArticleSearch.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/articles/<article_id>/feature/ (PIN)
    # ───────────────────────────────────────────────────────────────────────────
    # Pin article as featured. Feature limits: HERO(5), TOP(10), BREAKING(1), EDITOR_PICK(20) (PUBLISHER+)
    # Request: { "feature_type": "TOP", "rank": 1, "section": "academics" }
    # Response 200 OK: { "status": "featured", "feature_id": 1, "feature_type": "TOP", "section": "academics", "rank": 1 }
    # Implementation: PinFeature.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # DELETE /api/django/cms/articles/<article_id>/feature/?feature_type=TOP&section=academics
    # ───────────────────────────────────────────────────────────────────────────
    # Unpin featured article. REQUIRED: ?feature_type=TOP&section=academics (PUBLISHER+)
    # Response 200 OK: { "status": "unfeatured", "deleted": 1 }
    # Implementation: UnpinFeature.delete()
    #
    path("api/django/cms/articles/", include("apps.articles.urls")),
    
    # ╔═══════════════════════════════════════════════════════════════════════════╗
    # ║ 3. JOBS API - Job Posting Management & Public Listings                   ║
    # ╚═══════════════════════════════════════════════════════════════════════════╝
    # Location: apps/jobs/ (views*.py, urls.py)
    #
    # ═════════════════════════════════════════════════════════════════════════════
    # ▌ CMS JOBS ENDPOINTS (PROTECTED - JWT REQUIRED) ▌
    # ═════════════════════════════════════════════════════════════════════════════
    #
    # ───────────────────────────────────────────────────────────────────────────
    # POST /api/django/cms/jobs/
    # ───────────────────────────────────────────────────────────────────────────
    # Create and immediately publish job (status=1) - direct publish (PUBLISHER+)
    # Request Body (Required: title, slug, job_type, application_end_date, job_description):
    # { "title": "Senior Developer", "slug": "senior-dev-2026", "job_type": "GOVT", "application_end_date": "2026-03-31", "job_description": "..." }
    # Response 201 Created: { "id": 15, "status": "PUBLISHED", "message": "Job created and published successfully" }
    # Implementation: CreateJob.post()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/jobs/list/
    # ───────────────────────────────────────────────────────────────────────────
    # List all jobs for publisher with filters and cursor pagination (PUBLISHER+)
    # Query: ?status=1&job_type=GOVT&search=developer&limit=20&cursor=ABC
    # Filters: status (0/1), job_type (GOVT/PRIVATE), search (title/org/location)
    # Response 200 OK: { "results": [...], "next_cursor": "XYZ", "has_next": true, "limit": 20 }
    # Implementation: ListPublisherJobs.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/cms/jobs/<job_id>/detail/
    # ───────────────────────────────────────────────────────────────────────────
    # Get specific job details for CMS (PUBLISHER+)
    # Response 200 OK: Complete job object with all fields
    # Implementation: GetPublisherJob.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/jobs/<job_id>/
    # ───────────────────────────────────────────────────────────────────────────
    # Update job details (title, description, salary, location, etc.) (PUBLISHER+)
    # Request Body (All fields optional - only update what you send):
    # { "title": "Updated Title", "salary": "5-8 LPA", "job_description": "Updated description..." }
    # Response 200 OK: { "id": 15, "status": "UPDATED", "message": "Job updated successfully" }
    # Implementation: UpdateJob.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/jobs/<job_id>/publish/ ⚠️ NOT MAPPED IN URLS
    # ───────────────────────────────────────────────────────────────────────────
    # Publish job - set status=1 (PUBLISHER+)
    # Response 200 OK: { "status": "PUBLISHED" }
    # Implementation: PublishJob.patch() [EXISTS IN CODE BUT NOT MAPPED]
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/jobs/<job_id>/activate/
    # ───────────────────────────────────────────────────────────────────────────
    # Activate job - set status=1 (PUBLISHER+)
    # Response 200 OK: { "status": "ACTIVE" }
    # Implementation: ActivateJob.patch()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # PATCH /api/django/cms/jobs/<job_id>/deactivate/
    # ───────────────────────────────────────────────────────────────────────────
    # Deactivate job - set status=0 (PUBLISHER+)
    # Response 200 OK: { "status": "INACTIVE" }
    # Implementation: DeactivateJob.patch()
    #
    # ═════════════════════════════════════════════════════════════════════════════
    # ▌ JOBS PUBLIC ENDPOINTS (NO AUTH REQUIRED) ▌
    # ═════════════════════════════════════════════════════════════════════════════
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/jobs/
    # ───────────────────────────────────────────────────────────────────────────
    # List all active jobs with pagination. Filters: is_active=True, application_end_date >= today
    # Query: ?limit=20&offset=0
    # Response 200 OK: Array of job cards {id, title, slug, job_type, organization, location, salary, views_count, created_at}
    # Implementation: PublicJobList.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/jobs/filters/
    # ───────────────────────────────────────────────────────────────────────────
    # Get available filter options for job listing
    # Response 200 OK: {job_types: [...], organizations: [...], locations: [...], salary_ranges: [...]}
    # Implementation: PublicJobFilters.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/jobs/trending/?limit=10
    # ───────────────────────────────────────────────────────────────────────────
    # Trending jobs (most viewed)
    # Response 200 OK: [ { job_card }, { job_card }, ... ]
    # Implementation: TrendingJobs.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/jobs/search-suggestions/?q=developer
    # ───────────────────────────────────────────────────────────────────────────
    # Job title/skill autocomplete
    # Response 200 OK: [ "Senior Developer", "Developer Tools", ... ]
    # Implementation: JobSearchSuggestions.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/jobs/<slug>/
    # ───────────────────────────────────────────────────────────────────────────
    # Get single job detail (DETAIL PAGE). Tracks view event + increments view counter
    # Response 200 OK: Complete job object with id, title, slug, job_type, organization, location, salary, job_description, views_count, created_at, etc.
    # Error 404: { "error": "Job not found" }
    # Error 410: { "error": "Job not available" } - inactive or expired
    # Implementation: PublicJobDetailAPI.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /api/django/jobs/<slug>/seo/
    # ───────────────────────────────────────────────────────────────────────────
    # Get job SEO metadata + JSON-LD schema for search engine optimization
    # Response 200 OK: { "canonical": "...", "title": "...", "description": "...", "robots": "index,follow", "schema": {...} }
    # Error 404: { "error": "Job not found" }
    # Error 410: { "error": "Job not available" } - inactive or expired
    # Implementation: JobSEO.get()
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /jobs/<slug>/ (LEGACY - for direct website access)
    # ───────────────────────────────────────────────────────────────────────────
    # Alternative public job detail endpoint (same as /api/django/jobs/<slug>/)
    # Implementation: PublicJobDetail.get()
    #
    path("", include("apps.jobs.urls")),
    
    # ╔═══════════════════════════════════════════════════════════════════════════╗
    # ║ 4. SITEMAP - SEO XML Sitemap for Search Engines                          ║
    # ╚═══════════════════════════════════════════════════════════════════════════╝
    #
    # ───────────────────────────────────────────────────────────────────────────
    # GET /sitemap.xml
    # ───────────────────────────────────────────────────────────────────────────
    # XML sitemap for search engine crawlers (Google, Bing, etc.)
    # No authentication required
    #
    # Response 200 OK: Valid XML with published articles
    # Content-Type: application/xml
    #
    # Example response snippet:
    # <?xml version="1.0" encoding="UTF-8"?>
    # <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    #   <url>
    #     <loc>https://example.com/articles/tech/article-slug-1/</loc>
    #     <lastmod>2026-01-20T10:30:00Z</lastmod>
    #     <changefreq>weekly</changefreq>
    #     <priority>0.8</priority>
    #   </url>
    #   ...
    # </urlset>
    #
    # Implementation: Django Sitemap Framework via apps.articles.sitemaps::ArticleSitemap
    #
    # ═══════════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════════
    # SUMMARY - ENDPOINT AUDIT RESULTS
    # ═══════════════════════════════════════════════════════════════════════════
    # 
    # ✅ MAPPED ENDPOINTS (51 - Currently Active in urls.py):
    # TAXONOMY (10): 4 public + 6 CMS admin
    # ARTICLES (27): 15 CMS admin + 3 feature mgmt + 9 public
    # JOBS (13): 6 CMS admin + 7 public
    # SITEMAP (1): XML feed for SEO crawlers
    #
    # ⚠️  UNMAPPED ENDPOINTS (1 - Exists in code but not in urls.py):
    # JOBS: PublishJob (PATCH /api/django/cms/jobs/<job_id>/publish/)
    # DATABASE SCHEMA (As of 2026-01-24):
    # • public.articles_article: id, slug, section, status, summary, tags, keywords, canonical_url, meta_title, meta_description, noindex, og_title, og_description, og_image_url, expires_at, views_count, published_at, created_at, updated_at, created_by, updated_by
    # • public.articles_articletranslation: id, article_id, language, title, content
    # • public.taxonomy_category: id, section, name, slug, parent_id, rank, is_active, created_at, updated_at
    # • public.jobs_job: id, title, slug, job_type, organization, department, location, qualification, experience, vacancies, application_start_date, application_end_date, exam_date, job_description, eligibility, selection_process, salary, apply_url, is_active, views_count, created_at, updated_at
    # • public.jobs_jobviewevent: id, job_id, ip, user_agent, created_at
    #
    # ARTICLE URL PATHS NOTE:
    # • All article endpoints are included under /api/django/cms/articles/ prefix
    # • Public endpoints (no auth) mixed with CMS endpoints (auth required)
    # • URLs use relative paths in apps/articles/urls.py
    # • Examples:
    #   - POST /api/django/cms/articles/ [CMS - Create article]
    #   - GET /api/django/cms/articles/home/ [PUBLIC - Home feed]
    #   - GET /api/django/cms/articles/trending/ [PUBLIC - Trending articles]
    #   - GET /api/django/cms/articles/<section>/<slug>/ [PUBLIC - Article detail]
    #   - GET /api/django/cms/articles/list/ [PUBLIC - Cursor pagination, UNMAPPED]
    #
    # ═══════════════════════════════════════════════════════════════════════════
    # DETAILED BREAKDOWN
    # ═══════════════════════════════════════════════════════════════════════════
    #
    # TAXONOMY (10 mapped / 0 unmapped = 10 total):
    #   • 4 Public endpoints - Browse categories and hierarchy
    #   • 6 CMS endpoints - Create/Update/Delete/Enable/Disable categories
    #
    # ARTICLES (27 mapped / 0 unmapped = 27 total):
    #   • 15 CMS endpoints - Create, translation, media, categories, review, publish,
    #     deactivate, activate, reject, delete, delete-multi, search, admin-list,
    #     admin-search-suggestions, revisions
    #   • 3 Feature endpoints - Get features, pin, unpin
    #   • 9 Public endpoints - Home, section feed, list (cursor), trending, filters,
    #     search-suggestions, category-block, track-view, article detail
    #   • Multi-language support with fallback to Telugu (te)
    #
    # JOBS (13 mapped + 1 unmapped = 14 total):
    #   • 6 CMS endpoints - Create, list, detail, update, activate, deactivate
    #   • 1 UNMAPPED - PublishJob (exists in code but not in urls.py)
    #   • 7 Public endpoints - List, filter, trending, search, detail, legacy, SEO
    #   • View tracking and analytics
    #
    # SITEMAP (1 mapped):
    #   • XML sitemap for SEO crawlers
    #
    # ═══════════════════════════════════════════════════════════════════════════
    # KEY CONCEPTS FOR FRONTEND DEVELOPERS
    # ═══════════════════════════════════════════════════════════════════════════
    #
    # ARTICLE CARD STRUCTURE (used in list endpoints):
    # {
    #   "id": 42,
    #   "slug": "article-slug",
    #   "section": "academics",
    #   "title": "Article Title",
    #   "summary": "Brief summary of the article...",
    #   "image": "https://cdn.example.com/image.jpg",
    #   "published_at": "2026-01-15T10:00:00Z",
    #   "views_count": 245,
    #   "tags": ["tag1", "tag2"]
    # }
    #
    # JOB CARD STRUCTURE (used in list endpoints):
    # {
    #   "id": 15,
    #   "title": "Senior Developer",
    #   "slug": "senior-dev-2026",
    #   "job_type": "Full-time",
    #   "organization": "Tech Corp",
    #   "location": "Bangalore",
    #   "salary": "10-15 LPA",
    #   "views_count": 125,
    #   "application_end_date": "2026-03-31"
    # }
    #
    # AUTHENTICATION:
    # • All /api/django/cms/* endpoints require JWT authorization header
    # • All /api/django/* and / public endpoints are open (no auth)
    # • Format: Authorization: Bearer <jwt_token>
    # • JWT contains: user_id, username, role, email
    #
    # ROLE HIERARCHY:
    # • CONTRIBUTOR: Can create articles (minimum permission level)
    # • EDITOR: Can review and edit articles (higher than CONTRIBUTOR)
    # • PUBLISHER: Can publish articles and manage jobs (higher than EDITOR)
    # • ADMIN: Can create jobs, manage categories, access all features (highest)
    #
    # ARTICLE WORKFLOW:
    # • DRAFT → REVIEW (via /review/ endpoint) → PUBLISHED (via /publish/ endpoint)
    # • Can DEACTIVATE from PUBLISHED to hide articles (sets noindex=True)
    # • Featured articles can be pinned with rank (via /feature/ endpoint)
    # • Features: TOP, HERO, BREAKING, EDITOR_PICK (max limits enforced)
    # • Ranks auto-normalized when exceeded (older ranks decrease)
    #
    # JOB WORKFLOW:
    # • Created with is_active=False (DRAFT status)
    # • Can PUBLISH/ACTIVATE to make is_active=True (visible publicly)
    # • Can DEACTIVATE to set is_active=False (hidden from public)
    # • Must have application_end_date >= today to appear publicly
    # • Automatically tracks view events and increments view counter
    #
    # MULTI-LANGUAGE SUPPORT:
    # • Default language: Telugu (te)
    # • Supported: English (en), Hindi (hi)
    # • Fallback: If requested language unavailable, returns default "te"
    # • Query parameter: ?lang=en
    # • Article translations created via /translation/ endpoint
    #
    # PAGINATION:
    # • Offset-based: Use ?limit=N&offset=M (default 20, max 50)
    # • Cursor-based: Use ?limit=N&cursor=ABC (for efficiency on large datasets)
    # • Response includes next_cursor if more results available
    #
    # ERROR CODES:
    # • 200 OK: Success (GET, PATCH with updates)
    # • 201 Created: Resource created (POST)
    # • 204 No Content: Success (DELETE)
    # • 400 Bad Request: Invalid data or missing required fields
    # • 401 Unauthorized: No JWT token provided
    # • 403 Forbidden: Insufficient role/permissions for this action
    # • 404 Not Found: Resource not found or doesn't exist
    # • 410 Gone: Resource expired or no longer available (article inactive/expired)
    # • 500 Server Error: Backend issue - contact support
    #
    # COMMON REQUEST HEADERS:
    # Authorization: Bearer <jwt_token>          [For protected endpoints]
    # Content-Type: application/json              [For POST/PATCH requests]
    # Accept-Language: te,en;q=0.9               [Optional, for language preference]
    #
    # COMMON QUERY PARAMETERS:
    # ?lang=te                                   [Language: te, en, hi]
    # ?limit=20                                  [Results per page, max 50]
    # ?offset=0                                  [Pagination offset]
    # ?cursor=ABC                                [Cursor for cursor-based pagination]
    # ?section=academics                         [Filter by section]
    # ?search=django                             [Search query]
    #
    #
    path("sitemap.xml", sitemap, {"sitemaps": {"articles": ArticleSitemap, "jobs": JobsSitemap}}),
    path("api/django/academics/", include("apps.academics.urls")),
    path("api/django/media/", include("apps.media.urls")),
]