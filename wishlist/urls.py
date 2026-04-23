from django.urls import path
from . import views
app_name = "wishlist"

urlpatterns = [
    path("wishlist/products/", views.ProductWishlistListView.as_view(), name="product-list"),
    path("wishlist/products/<int:product_id>/toggle/", views.ProductWishlistToggleView.as_view(), name="product-toggle"),
    path("wishlist/videos/", views.VideoWishlistListView.as_view(), name="video-list"),
    path("wishlist/videos/<int:video_id>/toggle/", views.VideoWishlistToggleView.as_view(), name="video-toggle"),
]