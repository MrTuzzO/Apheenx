from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'videos', VideoViewSet, basename='video')
router.register(r'video-categories', VideoCategoryViewSet, basename='video-category')

urlpatterns = [
    path('', include(router.urls)),
    # Video access & streaming 
    path('videos/<int:video_id>/access/', VideoAccessCheckView.as_view()),
    path('videos/<int:video_id>/stream/', VideoStreamView.as_view()),
]