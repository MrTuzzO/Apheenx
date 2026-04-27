from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from product.models import Product
from video.models import Video
from .models import WishlistItem
from .serializers import ProductWishlistSerializer, VideoWishlistSerializer


def _ct(model):
    # Django caches this in-process after first call — zero extra DB hits
    return ContentType.objects.get_for_model(model)


class ProductWishlistListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductWishlistSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()

        # Step 1: one tiny query — just the IDs
        wishlisted_ids = (
            WishlistItem.objects
            .filter(user=self.request.user, content_type=_ct(Product))
            .values_list("object_id", flat=True)
        )

        # Step 2: fetch actual products with all relations in 3 queries total
        # (products + category via select_related + images via prefetch)
        return (
            Product.objects
            .filter(id__in=wishlisted_ids, status="active")
            .select_related("category")
            .prefetch_related("images")
            .only(
                "id", "name", "slug", "price", "price_off",
                "is_featured", "category__name",
            )
        )


class ProductWishlistToggleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT})
    def post(self, request, product_id):
        get_object_or_404(Product, pk=product_id, status="active")
        ct = _ct(Product)

        # Attempt delete first — if deleted, it was in wishlist
        deleted, _ = WishlistItem.objects.filter(
            user=request.user,
            content_type=ct,
            object_id=product_id,
        ).delete()

        if deleted:
            return Response(
                {"action": "removed", "product_id": product_id},
                status=status.HTTP_200_OK,
            )

        try:
            WishlistItem.objects.create(
                user=request.user,
                content_type=ct,
                object_id=product_id,
            )
        except IntegrityError:
            # Race condition — already added by concurrent request
            return Response(
                {"action": "added", "product_id": product_id},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"action": "added", "product_id": product_id},
            status=status.HTTP_201_CREATED,
        )


class VideoWishlistListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VideoWishlistSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Video.objects.none()

        # Step 1: one tiny query — just the IDs
        wishlisted_ids = (
            WishlistItem.objects
            .filter(user=self.request.user, content_type=_ct(Video))
            .values_list("object_id", flat=True)
        )

        # Step 2: fetch actual videos with category in 2 queries total
        return (
            Video.objects
            .filter(id__in=wishlisted_ids, status="published")
            .select_related("category")
            .only(
                "id", "title", "slug", "price", "thumbnail",
                "duration", "views_count", "is_featured", "category__name",
            )
        )


class VideoWishlistToggleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT})
    def post(self, request, video_id):
        get_object_or_404(Video, pk=video_id, status="published")
        ct = _ct(Video)

        deleted, _ = WishlistItem.objects.filter(
            user=request.user,
            content_type=ct,
            object_id=video_id,
        ).delete()

        if deleted:
            return Response(
                {"action": "removed", "video_id": video_id},
                status=status.HTTP_200_OK,
            )

        try:
            WishlistItem.objects.create(
                user=request.user,
                content_type=ct,
                object_id=video_id,
            )
        except IntegrityError:
            return Response(
                {"action": "added", "video_id": video_id},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"action": "added", "video_id": video_id},
            status=status.HTTP_201_CREATED,
        )
