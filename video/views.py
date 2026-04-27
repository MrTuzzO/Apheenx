import os
import mimetypes
from django.db.models import F
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from user.permission import IsAdminOrReadOnly
from .models import Video, VideoCategory, VideoOrder
from .serializers import *
from django.http import StreamingHttpResponse
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.static import serve
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

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request, video_id):
        has_access = VideoOrder.objects.filter(
            user=request.user,
            video_id=video_id,
            payment_status='captured'
        ).exists()
        return Response({"video_id": video_id, "has_access": has_access})


class VideoStreamView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.BINARY})
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

        # Absolute path + existence check
        filepath = os.path.join(settings.MEDIA_ROOT, str(video.main_video))
        if not os.path.exists(filepath):
            return Response(
                {"detail": "Video file not found on server."},
                status=status.HTTP_404_NOT_FOUND
            )

        file_size = os.path.getsize(filepath)
        content_type, _ = mimetypes.guess_type(filepath)
        content_type = content_type or 'video/mp4'

        range_header = request.META.get('HTTP_RANGE', '').strip()

        if range_header:
            #  Partial content (seeking) 
            try:
                range_val = range_header.replace('bytes=', '')
                start_str, end_str = range_val.split('-')
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                end = min(end, file_size - 1)
            except (ValueError, AttributeError):
                return Response(
                    status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
                )

            if start > end or start >= file_size:
                return Response(
                    status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
                )

            length = end - start + 1

            def range_iterator(path, start, length, chunk=8192):
                with open(path, 'rb') as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        data = f.read(min(chunk, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            response = StreamingHttpResponse(
                range_iterator(filepath, start, length),
                content_type=content_type,
                status=206
            )
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Content-Length'] = length

        else:
            #  Full file 
            def full_iterator(path, chunk=8192):
                with open(path, 'rb') as f:
                    while True:
                        data = f.read(chunk)
                        if not data:
                            break
                        yield data

            response = StreamingHttpResponse(
                full_iterator(filepath),
                content_type=content_type,
                status=200
            )
            response['Content-Length'] = file_size

        #  Security headers 
        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = 'inline'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['X-Frame-Options'] = 'SAMEORIGIN'

        return response

def protected_video_media(request, path):
    if not request.user.is_staff:
        raise PermissionDenied
    return serve(request, path, document_root=os.path.join(settings.MEDIA_ROOT, 'videos'))
