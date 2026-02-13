# apps/articles/views_attach.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.common.jwt import get_user_from_jwt
from apps.common.permissions import require_min_role
from apps.articles.models import Article
from apps.articles.serializers import ArticleMediaSerializer


class AttachMediaToArticle(APIView):
    """
    POST /api/cms/articles/<id>/media/
    role: EDITOR+   
    body:
    {
      "media_id": 123,
      "usage": "INLINE",
      "position": 1
    }
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = get_user_from_jwt(request)
        require_min_role(user, "EDITOR")

    def post(self, request, article_id):
        article = get_object_or_404(Article, id=article_id)

        serializer = ArticleMediaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ CMS DOES NOT VALIDATE MEDIA EXISTENCE
        # Media service owns that responsibility
        serializer.save(article=article)

        return Response(
            {"status": "attached", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )
