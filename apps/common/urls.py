from django.urls import path
from .welcome_view import welcome

urlpatterns = [
    path("welcome", welcome),
]
