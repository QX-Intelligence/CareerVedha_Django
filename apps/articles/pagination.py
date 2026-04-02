from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

class BaseCursorPagination(CursorPagination):
    page_size_query_param = "limit"
    max_page_size = 100

    def get_paginated_response(self, data):
        next_link = self.get_next_link()
        next_cursor = None
        if next_link:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(next_link)
            qs = parse_qs(parsed.query)
            if 'cursor' in qs:
                next_cursor = qs['cursor'][0]

        return Response({
            "results": data,
            "next_cursor": next_cursor,
            "has_next": next_link is not None,
            "limit": self.page_size
        })

class ArticleCursorPagination(BaseCursorPagination):
    page_size = 20
    ordering = ["-created_at", "-id"]

class ArticleRevisionCursorPagination(BaseCursorPagination):
    page_size = 50
    ordering = ["-created_at", "-id"]

class TrendingArticlesPagination(BaseCursorPagination):
    page_size = 20
    ordering = ["-views_count", "-published_at", "-id"]

class PublicArticlesPagination(BaseCursorPagination):
    page_size = 20
    ordering = ["-id"]

class ArticleFeatureCursorPagination(BaseCursorPagination):
    page_size = 50
    ordering = ["rank", "-id"]

class ArticleSearchPagination(BaseCursorPagination):
    page_size = 20
    ordering = ["-article__created_at", "-id"]
