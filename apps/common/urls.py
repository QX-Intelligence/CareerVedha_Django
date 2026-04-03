from django.urls import path
from .welcome_view import welcome

urlpatterns = [
    path("api/django/welcome/test", welcome),
]
