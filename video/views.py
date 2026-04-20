from django.db.models import F
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from user.permission import IsAdminOrReadOnly
from .models import Video, VideoCategory, VideoUnlock
from .serializers import (
    VideoCategorySerializer,
    VideoDetailSerializer,
    VideoListSerializer,
)


class VideoCategoryViewSet(viewsets.ModelViewSet):
    queryset = VideoCategory.objects.all().order_by('name')
    serializer_class = VideoCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'


class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.select_related('category')
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {'category__slug': ['exact'], 'is_featured': ['exact']}
    search_fields = ['title', 'description', 'category__name']
    ordering_fields = ['created_at', 'views_count', 'price']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_staff:
            return qs
        return qs.filter(status='published')

    def get_serializer_class(self):
        if self.action == 'list':
            return VideoListSerializer
        return VideoDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Video.objects.filter(pk=instance.pk).update(views_count=F('views_count') + 1)
        instance.refresh_from_db(fields=['views_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


    @action(detail=False, methods=['get'], url_path='my-unlocked', permission_classes=[IsAuthenticated])
    def my_unlocked(self, request):
        unlocked_ids = VideoUnlock.objects.filter(user=request.user).values_list('video_id', flat=True)
        queryset = self.get_queryset().filter(pk__in=unlocked_ids)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = VideoListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = VideoListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
