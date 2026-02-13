# apps/media/views_upload.py
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from apps.common.jwt import get_user_from_jwt
from apps.common.permissions import require_min_role

from django.conf import settings
from .models import MediaAsset
from .s3 import get_s3_client
from .utils import detect_media_type
from .pagination import MediaCursorPagination


class UploadMedia(APIView):
    """
    POST /api/media/upload/
    role: PUBLISHER+
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

        file = request.FILES.get("file")
        if not file:
            return Response({"error": "file required"}, status=400)

        purpose = request.data.get("purpose", "general")
        section = request.data.get("section", "")
        media_type = request.data.get("media_type")
        title = request.data.get("title", file.name)
        alt_text = request.data.get("alt_text", "")

        if not media_type:
            media_type = detect_media_type(file.name)
        
        valid_types = [c[0] for c in MediaAsset.MEDIA_TYPE_CHOICES]
        if media_type not in valid_types:
            return Response(
                {"error": f"Unsupported or invalid file format for '{file.name}'"}, 
                status=400
            )

        ext = file.name.split(".")[-1]
        key = f"media/{purpose}/{section}/{uuid.uuid4()}.{ext}"

        s3 = get_s3_client()
        s3.upload_fileobj(
            file,
            settings.AWS_STORAGE_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": file.content_type},
        )

        asset = MediaAsset.objects.create(
            file_key=key,
            file_size=file.size,
            content_type=file.content_type,
            title=title,
            alt_text=alt_text,
            media_type=media_type,
            purpose=purpose,
            section=section,
            uploaded_by_user_id=str(user["user_id"]),
            uploaded_by_role=user["role"],
        )

        return Response(
            {
                "media_id": asset.id,
                "media_type": asset.media_type,
                "file_key": asset.file_key,
            },
            status=status.HTTP_201_CREATED,
        )


class ListMedia(APIView):
    """
    GET /api/media/
    role: PUBLISHER+
    """
    def get(self, request):
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

        purpose = request.query_params.get("purpose")
        media_type = request.query_params.get("media_type")
        q = request.query_params.get("q")
        
        assets = MediaAsset.objects.filter(is_deleted=False).order_by("-created_at")
        
        if purpose:
            assets = assets.filter(purpose=purpose)
        if media_type:
            assets = assets.filter(media_type=media_type)
        if q:
            assets = assets.filter(title__icontains=q)

        paginator = MediaCursorPagination()
        paginated_assets = paginator.paginate_queryset(assets, request)

        from .utils import get_media_url
        
        result = []
        for asset in paginated_assets:
            result.append({
                "id": asset.id,
                "title": asset.title,
                "url": get_media_url(asset),
                "media_type": asset.media_type,
                "file_size": asset.file_size,
                "purpose": asset.purpose,
                "section": asset.section,
                "created_at": asset.created_at,
            })
            
        return paginator.get_paginated_response(result)


class DeleteMedia(APIView):
    """
    DELETE /api/media/<id>/
    role: PUBLISHER+
    """
    def delete(self, request, media_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")
        
        try:
            asset = MediaAsset.objects.get(id=media_id, is_deleted=False)
            asset.soft_delete()
            return Response({"message": "Media deleted successfully"})
        except MediaAsset.DoesNotExist:
            return Response({"error": "Media not found"}, status=404)


class ReplaceMedia(APIView):
    """
    PATCH /api/media/<id>/replace/
    role: PUBLISHER+
    """
    parser_classes = (MultiPartParser, FormParser)

    def patch(self, request, media_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

        try:
            asset = MediaAsset.objects.get(id=media_id, is_deleted=False)
        except MediaAsset.DoesNotExist:
            return Response({"error": "Media not found"}, status=404)

        title = request.data.get("title")
        alt_text = request.data.get("alt_text")
        file = request.FILES.get("file")

        if title:
            asset.title = title
        if alt_text is not None:
            asset.alt_text = alt_text

        if file:
            media_type = detect_media_type(file.name)
            valid_types = [c[0] for c in MediaAsset.MEDIA_TYPE_CHOICES]
            if media_type not in valid_types:
                return Response({"error": "Invalid file format"}, status=400)
            
            ext = file.name.split(".")[-1]
            purpose = asset.purpose
            section = asset.section
            new_key = f"media/{purpose}/{section}/{uuid.uuid4()}.{ext}"

            s3 = get_s3_client()
            s3.upload_fileobj(
                file,
                settings.AWS_STORAGE_BUCKET_NAME,
                new_key,
                ExtraArgs={"ContentType": file.content_type},
            )
            
            asset.file_key = new_key
            asset.file_size = file.size
            asset.content_type = file.content_type
            asset.media_type = media_type

        asset.save()

        return Response({
            "media_id": asset.id,
            "message": "Media updated successfully"
        })


class GetPresignedURL(APIView):
    """
    GET /api/media/<id>/presigned/
    role: PUBLISHER+
    """
    def get(self, request, media_id):
        user = get_user_from_jwt(request)
        require_min_role(user, "PUBLISHER")

        try:
            asset = MediaAsset.objects.get(id=media_id, is_deleted=False)
        except MediaAsset.DoesNotExist:
            return Response({"error": "Media not found"}, status=404)

        from .utils import get_media_url
        url = get_media_url(asset)

        return Response({
            "id": asset.id,
            "presigned_url": url,
            "expires_in": 3600
        })
