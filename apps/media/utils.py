import os
import uuid
from django.conf import settings
from .models import MediaAsset
from .s3 import get_s3_client

def detect_media_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    for mtype, extensions in MediaAsset.MEDIA_TYPE_EXTENSIONS.items():
        if ext in extensions:
            return mtype
    return "general"


def upload_media_file(file_obj, prefix, purpose, user_id, section=None):
    """
    Standardized helper for S3 upload + MediaAsset creation.
    """
    mtype = detect_media_type(file_obj.name)
    ext = os.path.splitext(file_obj.name)[1].lstrip(".").lower()
    if not ext: ext = "bin"
    
    # Structure: media/{prefix}/{optional_section}/{uuid}.{ext}
    key_path = f"media/{prefix}"
    if section:
        key_path += f"/{section}"
    
    key = f"{key_path}/{uuid.uuid4()}.{ext}"
    
    s3 = get_s3_client()
    s3.upload_fileobj(
        file_obj,
        settings.AWS_STORAGE_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": file_obj.content_type},
    )
    
    asset = MediaAsset.objects.create(
        file_key=key,
        file_size=file_obj.size,
        content_type=file_obj.content_type,
        title=f"Uploaded {prefix} file {file_obj.name}",
        media_type=mtype,
        purpose=purpose,
        section=section or "",
        uploaded_by_user_id=user_id or "",
    )
    return asset


def get_media_url(media_asset):
    """Generates a presigned URL for a MediaAsset."""
    if not media_asset: return None
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": media_asset.file_key,
        },
        ExpiresIn=3600,
    )
