from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from video.views import protected_video_media
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('media/videos/<path:path>', protected_video_media, name='protected-video-media'),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema")),

    path('api/v1/auth/', include('user.urls')),
    path('api/v1/', include('product.urls')),
    path('api/v1/', include('video.urls')),
    path('api/v1/', include('order.urls')),
    path('api/v1/', include('wishlist.urls')),
    path('api/v1/', include('core.urls')),
    path('api/v1/', include('announcement.urls')),

    # re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    # re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

