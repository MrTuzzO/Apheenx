from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem, Order
from .serializers import *
from product.models import Product
from user.permission import IsAdmin


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_cart(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    def list(self, request):
        cart = self._get_cart(request.user)
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'], url_path='items')
    def add_item(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = self._get_cart(request.user)
        product = get_object_or_404(Product, id=serializer.validated_data['product_id'], status='active')
        quantity = serializer.validated_data['quantity']
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=['quantity', 'updated_at'])
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path=r'items/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = self._get_cart(request.user)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.quantity = serializer.validated_data['quantity']
        item.save(update_fields=['quantity', 'updated_at'])
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['delete'], url_path=r'items/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        cart = self._get_cart(request.user)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        cart = self._get_cart(request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart).data)


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related('items__product')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return CheckoutSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

# For admin order management
class AdminOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdmin]
    serializer_class = AdminOrderSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = (
            Order.objects
            .select_related('user')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def partial_update(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = AdminOrderSerializer(
            order,
            data={'status': request.data.get('status')},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

