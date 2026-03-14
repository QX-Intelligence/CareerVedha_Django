
import json
from django.utils.timezone import now
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.common.permissions import HasMinRole, IsAuthenticatedDict
from apps.common.authentication import JWTAuthentication
from .models import TopStory
from .serializers import TopStorySerializer

class TopStoryAdminViewSet(viewsets.ModelViewSet):
    """
    CMS CRUD for Top Stories.
    Only ADMIN+ can manage.
    """
    queryset = TopStory.objects.all().prefetch_related('media_links__media', 'category').order_by("rank", "-publish_date", "-id")
    serializer_class = TopStorySerializer
    authentication_classes = [JWTAuthentication]
    
    def get_permissions(self):
        # Using the dynamic role checker
        return [IsAuthenticatedDict(), HasMinRole("ADMIN")]


    def perform_create(self, serializer):
        serializer.save()

class TopStoryPublicView(APIView):
    """
    Public API for dashboard Top Stories.
    Filters by is_top_story=True, non-expired, and ordered by publish_date.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        limit = int(request.GET.get("limit", 5))
        category = request.GET.get("category")
        
        qs = TopStory.objects.prefetch_related(
            'media_links__media', 
            'category'
        ).filter(
            is_top_story=True,
            publish_date__lte=now()
        )
        
        # Expiry filter
        qs = qs.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gt=now()))
        
        if category:
            qs = qs.filter(category__slug__iexact=category)
            
        qs = qs.order_by("rank", "-publish_date", "-id")[:limit]
        
        serializer = TopStorySerializer(qs, many=True)
        return Response({"results": serializer.data})
