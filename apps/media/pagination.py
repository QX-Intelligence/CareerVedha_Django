from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

class MediaCursorPagination(CursorPagination):
    page_size = 15
    page_size_query_param = "limit"
    max_page_size = 100
    ordering = ["-created_at", "-id"]

    def get_paginated_response(self, data):
        return Response({
            "results": data,
            "next_cursor": self.get_next_link().split("cursor=")[1] if self.get_next_link() and "cursor=" in self.get_next_link() else None,
            "has_next": self.get_next_link() is not None,
            "limit": self.page_size
        })
