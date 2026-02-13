# apps/media/urls.py
from django.urls import path
from . import views_upload

urlpatterns = [
    path("", views_upload.ListMedia.as_view(), name="media-list"),
    path("upload/", views_upload.UploadMedia.as_view(), name="media-upload"),
    path("<int:media_id>/", views_upload.DeleteMedia.as_view(), name="media-delete"),
    path("<int:media_id>/replace/", views_upload.ReplaceMedia.as_view(), name="media-replace"),
    path("<int:media_id>/presigned/", views_upload.GetPresignedURL.as_view(), name="media-presigned"),
]
