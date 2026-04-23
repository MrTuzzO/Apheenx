from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Order
from .serializers import AdminOrderSerializer, CheckoutSerializer, OrderSerializer
from user.permission import IsAdmin


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
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
            qs = qs.filter(order_status=status_filter)
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

