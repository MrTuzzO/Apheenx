from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from video.views import protected_video_media

schema_view = get_schema_view(
    openapi.Info(
        title="Apheenx API",
        default_version='v1',
        description="API documentation",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('media/videos/<path:path>', protected_video_media, name='protected-video-media'),

    path('api/v1/auth/', include('user.urls')),
    path('api/v1/', include('product.urls')),
    path('api/v1/', include('video.urls')),
    path('api/v1/', include('order.urls')),
    path('api/v1/', include('wishlist.urls')),
    path('api/v1/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

