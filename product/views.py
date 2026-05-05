from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import ProductCategory, Product, ProductImage
from .serializers import ProductCategorySerializer, ProductListSerializer, ProductDetailSerializer
from user.permission import IsAdminOrReadOnly, IsAdmin
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').prefetch_related('images')
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {'category__slug': ['exact'], 'status': ['exact'], 'is_featured': ['exact'], 'price_off': ['gt']}
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['price', 'created_at', 'stock']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_staff:
            return qs
        return qs.filter(status='active')

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        for image in request.FILES.getlist('images'):
            ProductImage.objects.create(product=product, image=image)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='images/add', permission_classes=[IsAdmin])
    def add_images(self, request, slug=None):
        product = self.get_object()
        images = request.FILES.getlist('images')
        if not images:
            return Response({"detail": "No images provided."}, status=400)
        for image in images:
            ProductImage.objects.create(product=product, image=image)
        return Response(ProductDetailSerializer(product, context={'request': request}).data)

    @action(detail=True, methods=['delete'], url_path='images/(?P<image_id>[^/.]+)', permission_classes=[IsAdmin])
    def delete_image(self, request, slug=None, image_id=None):
        product = self.get_object()
        image = get_object_or_404(ProductImage, id=image_id, product=product)
        image.delete()
        return Response({"detail": "Image deleted."}, status=204)
