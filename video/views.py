from django.db.models import F
from rest_framework import filters, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from user.permission import IsAdminOrReadOnly
from .models import Video, VideoCategory, VideoOrder
from .serializers import *
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404


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
        unlocked_ids = VideoOrder.objects.filter(user=request.user, payment_status='captured').values_list('video_id', flat=True)
        queryset = self.get_queryset().filter(pk__in=unlocked_ids)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = VideoListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = VideoListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)



class VideoAccessCheckView(APIView):
    """
    GET /api/payments/videos/{video_id}/access/
    Frontend uses this to show Buy vs Play button.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, video_id):
        has_access = VideoOrder.objects.filter(
            user=request.user,
            video_id=video_id,
            payment_status='captured'
        ).exists()
        return Response({"video_id": video_id, "has_access": has_access})


class VideoStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, video_id):
        video = get_object_or_404(Video, id=video_id, status='published')

        has_access = VideoOrder.objects.filter(
            user=request.user,
            video=video,
            payment_status='captured'
        ).exists()

        if not has_access:
            return Response(
                {"detail": "Purchase this video to watch it."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not video.main_video:
            return Response(
                {"detail": "Video file not available."},
                status=status.HTTP_404_NOT_FOUND
            )

        def file_iterator(file_field, chunk_size=8192):
            file_field.open('rb')
            try:
                while True:
                    chunk = file_field.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            finally:
                file_field.close()

        response = StreamingHttpResponse(
            file_iterator(video.main_video),
            content_type='video/mp4',
        )
        response['Content-Disposition'] = 'inline'          # blocks download
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response['Pragma'] = 'no-cache'

        if video.main_video.size:
            response['Content-Length'] = video.main_video.size
            response['Accept-Ranges'] = 'bytes'

        return response
